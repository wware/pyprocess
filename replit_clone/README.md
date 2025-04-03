# Replit Clone

> (Referring to the example.py file in the root directory)
> Here's an example of how I like to define types as pydantic models, and
> interfaces using ABC classes. I want something like this for a locally-run
> Replit clone that I can write in python and run across my LAN. Can you
> design a system like that at the types-and-interfaces level like this?

I'll help design a similar architecture for a local Replit-like system.
We'll focus on defining the core models and interfaces that would be needed
for code execution, file management, and session handling.

This design provides the core building blocks for a Replit-like system:

- Project Management: Project model and ProjectStorage interface for managing workspaces
- File Handling: File model and FileStorage interface for file operations
- Code Execution: CodeExecutor interface for running code with ExecutionResult tracking
- Environment Management: RuntimeEnvironment interface for handling isolated execution environments

You could implement these interfaces with:

- ProjectStorage: SQLite or file system storage
- FileStorage: Local filesystem with project directories
- CodeExecutor: Process-based execution using subprocess or container-based execution using Docker
- RuntimeEnvironment: Virtual environments for Python, Node.js for JavaScript, etc.

The system supports basic features like:

- Multiple projects per user
- File management within projects
- Code execution with output capture
- Language-specific environment isolation
- Resource usage monitoring

## So I banged on this a bit more

I prompted the AI (the assistant in Cursor IDE) to generate a types-and-interfaces
level architecture for the Replit clone. I prompted it to improve the documentation
and comments.

> Based on what is in models.py, please write two things.
> (1) A schema for a SQLite database for this thing. You can assume SQLite will use a
> file on the local hard drive.
> (2) A comprehensive set of pytest test cases. Everything so far is interfaces, so
> feel free to use dependency injection and define whatever mock objects you need.

## Testing

To run the tests, you have several options:

Basic test run (uses all mocks):
```bash
pytest replit_clone/tests/
```

Test a specific real implementation (others mocked):
```bash
pytest replit_clone/tests/ --test-mode=project-storage
pytest replit_clone/tests/ --test-mode=file-storage
pytest replit_clone/tests/ --test-mode=code-executor
pytest replit_clone/tests/ --test-mode=runtime-env
```

Additional useful pytest options:
```bash
pytest replit_clone/tests/ -v         # verbose output
pytest replit_clone/tests/ -s         # show print statements
pytest replit_clone/tests/ -k "test_name"  # run specific test
pytest replit_clone/tests/ --pdb      # drop into debugger on failure
```

Remember to install required packages:
```bash
pip install pytest pytest-asyncio
```
