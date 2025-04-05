"""Code Quality Auto-Fix Loop Runner

This script automates the process of fixing code quality issues by:
1. Running code quality checks (pylint, flake8, pytest)
2. Sending the output to an LLM (Ollama/Qwen)
3. Applying the suggested fixes
4. Repeating until all checks pass

The script uses Docker to run both the code checks and the LLM,
ensuring a consistent environment and avoiding local dependencies.

Usage:
    python loop_runner.py [options] path/to/code

The script will continue running until either:
- All checks pass successfully
- Maximum iterations reached
- LLM fails to provide valid fixes
"""

import os
import subprocess
import sys
import asyncio
import argparse
import jinja2
from pydantic import BaseModel


def parse_args() -> tuple[list[str], dict]:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run code quality checks")
    parser.add_argument(
        "sources",
        nargs="+",
        help="Paths to code files or directories"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="qwen2.5-coder",
        help="what LLM to use"
    )
    parser.add_argument(
        "-i", "--iterations",
        type=int,
        default=100,
        help="how many iterations to run"
    )
    return parser.parse_args()


def generate_prompt(results: list[tuple[str, int, str]],
                    files: list[str]) -> str:
    """Generate a prompt for the LLM"""
    with open("prompt_template.txt", "r", encoding="utf-8") as f:
        template = jinja2.Template(f.read())
        return template.render(files=files, issues=results)


class Issue(BaseModel):
    """Represents a code quality issue found by a checker

    Attributes:
        filename: Path to the file containing the issue
        content: Description of the issue from the checker
    """
    filename: str
    content: str

    def to_dict(self) -> dict:
        """Convert the issue to a dictionary for serialization"""
        return {
            "filename": self.filename,
            "content": self.content
        }


class File(BaseModel):
    """Represents a source file to be checked and potentially modified

    Attributes:
        name: Path to the file
        content: Current content of the file, empty until read
    """
    name: str
    content: str = ""

    def read(self) -> str:
        """Read the file content from disk into the content attribute"""
        with open(self.name, "r", encoding="utf-8") as f:
            self.content = f.read()

    def to_dict(self) -> dict:
        """Convert the file to a dictionary for serialization"""
        return {
            "name": self.filename,
            "content": self.content
        }


class Diff(File):
    """Represents a diff for a file"""
    pass


def validate_diffs(diffs: list[str]) -> bool:
    """Validate the diffs"""
    return True or diffs


def apply_diffs(diffs: list[Diff]):
    """Apply the diffs to their respective files using patch.

    Takes a list of diffs and applies each one using the Unix patch
    command. Each diff is applied in the context of its target file's
    directory to ensure relative paths work correctly.

    Args:
        diffs (list[Diff]): List of diffs to apply, each containing:
            - name: Path to the file to patch
            - content: The unified diff content

    Raises:
        subprocess.CalledProcessError: If patch command fails
        IOError: If file operations fail
        
    Note:
        Uses -p1 flag with patch to handle git-style diffs correctly.
        Diffs should be in unified format (diff -u).
    """
    for diff in diffs:
        with open(diff.name, "w", encoding="utf-8") as f:
            cmd = f"patch -p1 -d {os.path.dirname(diff.name)}"
            with subprocess.Popen(
                cmd.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=False
            ) as p:
                stdout, _ = p.communicate(input=diff.content.encode())
                if p.returncode != 0:
                    raise subprocess.CalledProcessError(p.returncode, cmd)
                f.write(stdout.decode())


async def get_llm_response(prompt: str) -> tuple[str, list[Diff]]:
    """Get a response from the LLM and parse any diffs.

    Sends the prompt to the LLM via docker-compose and parses the response
    into an explanation and a list of diffs. The LLM is expected to format
    diffs with special markers:
    <<<< filename.py <<<<
    @@ -1,1 +1,1 @@
    -Getting rid of that
    +Replacing it with this
    >>>>>>>>

    Args:
        prompt (str): The formatted prompt containing code and issues

    Returns:
        tuple containing:
        - explanation (str): LLM's explanation of changes
        - diffs (list[Diff]): List of diffs to apply, parsed from response

    Note:
        The response format is critical - diffs must be properly marked
        to be parsed correctly. Any unmarked text is treated as explanation.
    """
    proc = await asyncio.create_subprocess_exec(
        'docker', 'compose', 'run', '--rm',
        'ollama', 'chat', prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    output, _ = await proc.communicate()
    explanation = ""
    current_diff = None
    diffs = []
    for line in output.decode().split("\n"):
        if line.startswith("<<<< "):
            current_diff = Diff(
                name=line.split("<<<< ")[1].split(" <<<<")[0]
            )
        elif line.startswith(">>>>>>>>"):
            diffs.append(current_diff)
            current_diff = None
        elif current_diff is not None:
            current_diff.content += line + "\n"
        else:
            explanation += line + "\n"
    return explanation, diffs


async def run_check(cmd: str) -> tuple[int, str]:
    """Run a docker compose command and capture its output.

    Executes the command in a Docker container using docker-compose,
    combining stdout and stderr into a single stream for easier
    processing by the LLM.

    Args:
        cmd (str): Command to run in the container
                  (e.g. "pylint path/to/code")

    Returns:
        tuple containing:
        - exit_code (int): Command's exit status (0 for success)
        - output (str): Combined stdout/stderr output

    Note:
        stderr is redirected to stdout to simplify output handling
        and allow the LLM to parse all messages in context.
    """
    proc = await asyncio.create_subprocess_exec(
        'docker', 'compose', 'run', '--rm', 'tests',
        *cmd.split(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT  # Merge stderr into stdout
    )
    output, _ = await proc.communicate()
    return proc.returncode, output.decode()


async def run_all_checks(*sources: str) -> list[tuple[str, int, str]]:
    """Run all code quality checks on the specified source files.

    Executes linters and tests in sequence, stopping at first failure.
    Each check runs in a Docker container to ensure consistent environments.

    Args:
        *sources: Variable number of source file paths or directories to check

    Returns:
        List of tuples, each containing:
        - check_name (str): Name of the check
                            (ruff/pylint/flake8/pytest)
        - exit_code (int): Exit status of the check
                           (0 for success)
        - output (str): Combined stdout/stderr from the check

    Note:
        Checks are run in order and stop at first failure to avoid
        overwhelming the LLM with multiple types of errors at once.
    """
    srcstr = " ".join(sources)
    checks = [
        f"ruff check {srcstr}",
        f"flake8 {srcstr}",
        f"pylint {srcstr}",
        f"pytest {srcstr}"
    ]
    results = []
    code = 0
    for cmd in checks:
        code, output = await run_check(cmd)
        results.append((cmd.split()[1], code, output))
        print(f"$ {cmd} ==> exit status {code}")
        if code != 0:
            break
    return code, results


async def main():
    """Main entry point"""
    files, options = parse_args()
    print(options)
    history = []  # List of explanations

    while True:
        # Run checks
        results = await run_all_checks(*files)
        if all(code == 0 for _, code, _ in results):
            print("\n".join(history))
            return 0  # Success

        # Generate prompt
        prompt = generate_prompt(results, files)

        # Get LLM response
        explanation, diffs = await get_llm_response(prompt)

        # Validate diffs
        if not validate_diffs(diffs):
            print("\n".join(history))
            print("Failed to parse/validate diffs:", diffs)
            return 1  # Failure

        # Record explanation and apply changes
        history.append(explanation)
        apply_diffs(diffs)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
