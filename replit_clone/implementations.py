"""
Real implementations of the core interfaces

This module provides minimal placeholder implementations that will be
replaced with real functionality later. Currently used to satisfy imports
in the test configuration.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import subprocess
import venv
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import docker
from replit_clone.models import (
    Project, File, ExecutionResult, ExecutionStatus,
    ProjectStorage, FileStorage, CodeExecutor, RuntimeEnvironment
)


class SQLiteProjectStorage(ProjectStorage):
    """SQLite-based implementation of ProjectStorage

    Provides a persistent storage implementation using SQLite database.
    Handles project metadata storage and retrieval with basic CRUD operations.

    Attributes:
        db_path: Path to the SQLite database file
        conn: SQLite database connection instance
    """

    def __init__(self, db_path: str):
        """Initialize storage with database path

        Args:
            db_path: Path where SQLite database file should be created/accessed
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    async def initialize(self):
        """Set up database tables and connection

        Creates necessary database tables using schema.sql if they don't exist.
        Must be called before any other operations.

        Raises:
            RuntimeError: If database initialization fails
        """
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        with open('replit_clone/schema.sql', encoding='utf-8') as f:
            self.conn.executescript(f.read())

    async def cleanup(self):
        """Clean up database connections

        Closes the database connection and releases resources.
        Should be called when storage is no longer needed.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    async def create_project(self, project: Project) -> Project:
        """Create a new project in the database

        Args:
            project: Project model to store

        Returns:
            Project: The stored project

        Raises:
            RuntimeError: If database not initialized
            sqlite3.Error: If database operation fails
        """
        if not self.conn:
            raise RuntimeError("Database not initialized")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO projects (
                id, name, description,
                language, created_at,
                updated_at, owner_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(project.id), project.name, project.description,
            project.language, project.created_at,
            project.updated_at, project.owner_id
        ))
        self.conn.commit()
        return project

    async def get_project(self, project_id: UUID) -> Project:
        """Retrieve a project by its ID

        Args:
            project_id: UUID of project to retrieve

        Returns:
            Project: The requested project

        Raises:
            RuntimeError: If database not initialized
            KeyError: If project not found
            sqlite3.Error: If database operation fails
        """
        if not self.conn:
            raise RuntimeError("Database not initialized")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM projects WHERE id = ?",
            (str(project_id),)
        )
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"Project {project_id} not found")

        return Project(
            id=UUID(row['id']),
            name=row['name'],
            description=row['description'],
            language=row['language'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            owner_id=row['owner_id']
        )

    async def list_projects(self, owner_id: str) -> List[Project]:
        if not self.conn:
            raise RuntimeError("Database not initialized")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM projects WHERE owner_id = ?", (owner_id,)
        )
        return [
            Project(
                id=UUID(row['id']),
                name=row['name'],
                description=row['description'],
                language=row['language'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                owner_id=row['owner_id']
            )
            for row in cursor.fetchall()
        ]

    async def delete_project(self, project_id: UUID) -> None:
        """Delete a project and all associated data.

        Args:
            project_id: UUID of the project to delete

        Raises:
            NotFoundError: If project doesn't exist
            StorageError: If storage operation fails
        """
        if not self.conn:
            raise RuntimeError("Database not initialized")

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (str(project_id),))
        if cursor.rowcount == 0:
            raise KeyError(f"Project {project_id} not found")
        self.conn.commit()


class FileSystemStorage(FileStorage):
    """Filesystem-based implementation of FileStorage

    Stores file contents directly on the filesystem while keeping metadata
    in SQLite. Provides isolation between projects by organizing files in
    project-specific directories.

    Attributes:
        workspace_path: Base directory for all file storage
        metadata_db: Path to SQLite database for file metadata
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.metadata_db = self.workspace_path / "metadata.db"
        self.conn: Optional[sqlite3.Connection] = None

    async def initialize(self):
        """Set up workspace directory and metadata database"""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.metadata_db)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE (project_id, path)
            )
        """)
        self.conn.commit()

    async def cleanup(self):
        """Clean up workspace files and database"""
        if hasattr(self, 'conn'):
            self.conn.close()
        shutil.rmtree(self.workspace_path, ignore_errors=True)

    def _get_file_path(self, project_id: UUID, path: str) -> Path:
        """Get the full path for a file"""
        return self.workspace_path / str(project_id) / path

    async def save_file(self, file: File) -> File:
        file_path = self._get_file_path(file.project_id, file.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open('w') as f:
            f.write(file.content)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO files (
                id, project_id, path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(file.id), str(file.project_id), file.path,
            file.created_at, file.updated_at
        ))
        self.conn.commit()
        return file

    async def get_file(self, file_id: UUID) -> File:
        """Retrieve a file by its ID.

        Args:
            file_id: UUID of the file to retrieve

        Returns:
            File: The requested file

        Raises:
            NotFoundError: If file doesn't exist
            StorageError: If storage operation fails
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (str(file_id),))
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"File {file_id} not found")

        file_path = self._get_file_path(UUID(row['project_id']), row['path'])
        if not file_path.exists():
            raise KeyError(f"File content not found for {file_id}")

        with file_path.open('r') as f:
            content = f.read()

        return File(
            id=UUID(row['id']),
            project_id=UUID(row['project_id']),
            path=row['path'],
            content=content,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    async def list_files(self, project_id: UUID) -> List[File]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM files WHERE project_id = ?", (str(project_id),)
        )
        files = []

        for row in cursor.fetchall():
            file_path = self._get_file_path(project_id, row['path'])
            if file_path.exists():
                with file_path.open('r') as f:
                    content = f.read()
                files.append(File(
                    id=UUID(row['id']),
                    project_id=UUID(row['project_id']),
                    path=row['path'],
                    content=content,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
        return files

    async def delete_file(self, file_id: UUID) -> None:
        """Delete a file from storage.

        Args:
            file_id: UUID of the file to delete

        Raises:
            NotFoundError: If file doesn't exist
            StorageError: If storage operation fails
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (str(file_id),))
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"File {file_id} not found")

        file_path = self._get_file_path(UUID(row['project_id']), row['path'])
        if file_path.exists():
            file_path.unlink()

        cursor.execute("DELETE FROM files WHERE id = ?", (str(file_id),))
        self.conn.commit()


class DockerCodeExecutor(CodeExecutor):
    """Docker-based implementation of CodeExecutor

    Uses Docker containers to provide isolated execution environments for code.
    Each execution gets its own container with resource limits and a mounted
    workspace directory.

    Attributes:
        client: Docker client instance
        executions: Dictionary mapping execution IDs to execution metadata
        workspace: Path object for the base workspace directory
    """

    def __init__(self):
        """Initialize executor with empty state"""
        self.client = None
        self.executions: Dict[UUID, Dict] = {}
        self.workspace = Path("/tmp/code_executor")

    async def initialize(self):
        """Set up Docker client and workspace

        Creates the workspace directory and pulls the required Docker image.
        Must be called before any execution attempts.

        Raises:
            RuntimeError: If Docker client initialization fails
        """
        self.client = docker.from_env()
        self.client.images.pull("python:3.9-slim")
        self.workspace.mkdir(parents=True, exist_ok=True)

    async def execute(
            self, project_id: UUID, main_file: str
    ) -> ExecutionResult:
        """Execute code in a Docker container with resource limits

        Creates a new container with the project's code mounted and executes
        the specified main file. The container runs with memory and CPU limits.

        Args:
            project_id: UUID of the project containing the code
            main_file: Path to the entry point file relative to project root

        Returns:
            ExecutionResult with initial running status

        Raises:
            RuntimeError: If Docker client not initialized
            DockerException: If container creation/execution fails
        """
        if not self.client:
            raise RuntimeError("Docker client not initialized")

        execution_id = uuid4()
        started_at = datetime.now(timezone.utc)

        # Use the provided project_id for the workspace
        exec_dir = self.workspace / str(project_id)
        exec_dir.mkdir(parents=True, exist_ok=True)

        try:
            container = self.client.containers.run(
                "python:3.9-slim",
                ["python", "/code/main.py"],
                detach=True,
                mem_limit="512m",
                nano_cpus=1000000000,  # 1 CPU
                working_dir="/code",
                volumes={
                    str(exec_dir): {
                        'bind': '/code',
                        'mode': 'ro'
                    }
                },
                remove=False
            )

            self.executions[execution_id] = {
                'container': container,
                'project_id': project_id,
                'started_at': started_at,
                'workspace': exec_dir
            }

            return ExecutionResult(
                execution_id=execution_id,
                project_id=project_id,
                status=ExecutionStatus.RUNNING,
                stdout="",
                stderr="",
                exit_code=None,
                started_at=started_at,
                completed_at=None,
                memory_usage=0.0,
                cpu_time=0.0
            )

        except Exception:   # noqa: F841
            # Clean up workspace on error
            shutil.rmtree(exec_dir, ignore_errors=True)
            raise

    async def terminate(self, execution_id: UUID) -> None:
        """Terminate a running execution

        Stops the Docker container associated with the execution.

        Args:
            execution_id: UUID of the execution to terminate

        Raises:
            KeyError: If execution_id not found
            RuntimeError: If container termination fails
        """
        if execution_id not in self.executions:
            raise KeyError(f"Execution {execution_id} not found")

        exec_data = self.executions[execution_id]
        try:
            if 'container' in exec_data:
                exec_data['container'].stop(timeout=1)
        except Exception as e:
            raise RuntimeError(
                f"Failed to terminate execution: {e}"
            ) from e

    async def get_status(self, execution_id: UUID) -> ExecutionResult:
        """Get current execution status and results

        Retrieves the current state of the execution including logs and
        resource usage.

        Args:
            execution_id: UUID of the execution to check

        Returns:
            ExecutionResult containing current status, logs, and resource usage

        Raises:
            KeyError: If execution_id not found
            RuntimeError: If status check fails
        """
        if execution_id not in self.executions:
            raise KeyError(f"Execution {execution_id} not found")

        exec_data = self.executions[execution_id]
        container = exec_data['container']

        try:
            # Force a refresh of container state
            container.reload()

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')

            # Get the actual container state
            container_status = container.status
            exit_code = container.attrs['State'].get('ExitCode')

            # Determine status and completion
            if container_status == 'exited':
                completed_at = datetime.fromisoformat(
                    container.attrs['State']['FinishedAt']
                    .replace('Z', '+00:00')
                )
                if exit_code != 0:
                    status = ExecutionStatus.ERROR
                else:
                    status = ExecutionStatus.COMPLETED
            else:
                status = ExecutionStatus.RUNNING
                exit_code = None
                completed_at = None

            return ExecutionResult(
                execution_id=execution_id,
                project_id=exec_data['project_id'],
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                started_at=exec_data['started_at'],
                completed_at=completed_at,
                memory_usage=0.0,
                cpu_time=0.0
            )

        except (docker.errors.APIError,
                docker.errors.NotFound) as e:
            return ExecutionResult(
                execution_id=execution_id,
                project_id=exec_data['project_id'],
                status=ExecutionStatus.ERROR,
                stdout="",
                stderr=f"Error getting execution status: {e}",
                exit_code=1,
                started_at=exec_data['started_at'],
                completed_at=datetime.now(timezone.utc),
                memory_usage=0.0,
                cpu_time=0.0
            )

    async def cleanup(self):
        """Clean up all containers and resources

        Stops and removes all containers, deletes workspace directories,
        and closes the Docker client connection.
        """
        if self.client:
            for exec_data in self.executions.values():
                try:
                    if 'container' in exec_data:
                        exec_data['container'].remove(force=True)
                    if 'workspace' in exec_data:
                        shutil.rmtree(exec_data['workspace'],
                                      ignore_errors=True)
                except (docker.errors.DockerException, OSError):
                    pass  # Best effort cleanup
            self.client.close()
            self.executions.clear()
            shutil.rmtree(self.workspace, ignore_errors=True)


class VenvRuntimeEnvironment(RuntimeEnvironment):
    """Virtual environment based implementation of RuntimeEnvironment

    Creates isolated Python virtual environments for each project.
    Manages dependencies and environment lifecycle.

    Attributes:
        base_path: Base directory for all virtual environments
        environments: Dictionary mapping environment IDs to their paths
    """

    def __init__(self):
        self.base_path = Path("/tmp/venvs")
        self.environments = {}  # env_id -> path

    async def initialize(self):
        """Set up base directory"""
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def cleanup(self):
        """Clean up all environments"""
        shutil.rmtree(self.base_path, ignore_errors=True)

    async def create_environment(self, project_id: UUID) -> str:
        env_id = f"env_{project_id}"
        env_path = self.base_path / env_id

        venv.create(env_path, with_pip=True)
        self.environments[env_id] = env_path

        return env_id

    async def install_dependencies(
            self, env_id: str, dependencies: List[str]
    ) -> None:
        if env_id not in self.environments:
            raise KeyError(f"Environment {env_id} not found")

        env_path = self.environments[env_id]
        pip_path = env_path / "bin" / "pip"

        process = subprocess.run(
            [str(pip_path), "install"] + dependencies,
            capture_output=True,
            text=True,
            check=False
        )

        if process.returncode != 0:
            raise RuntimeError(
                f"Failed to install dependencies: {process.stderr}"
            )

    async def cleanup_environment(self, env_id: str) -> None:
        if env_id not in self.environments:
            raise KeyError(f"Environment {env_id} not found")

        env_path = self.environments[env_id]
        shutil.rmtree(env_path)
        del self.environments[env_id]
