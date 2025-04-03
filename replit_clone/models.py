"""
Core models and interfaces for the Replit Clone system

This module defines the fundamental data structures and interfaces for a local
Replit-like code execution environment. It provides:

    - Data Models:
        - Project and File representations using Pydantic
        - Execution status tracking
        - Language support definitions

    - Storage Interfaces:
        - Abstract project persistence layer
        - Abstract file management system
        - Support for different backend implementations

    - Execution Interfaces:
        - Code execution management
        - Runtime environment isolation
        - Resource tracking and monitoring

The interfaces are designed to be implementation-agnostic, allowing for
different storage backends (SQLite, filesystem, etc.) and execution
strategies (processes, containers, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    """Status of code execution

    Inherits from str for JSON serialization compatibility.
    Represents the lifecycle states of code execution.
    """
    QUEUED = "QUEUED"         # Execution requested but not yet started
    RUNNING = "RUNNING"       # Code is currently executing
    COMPLETED = "COMPLETED"   # Execution finished successfully
    ERROR = "ERROR"          # Execution terminated with an error


class Language(str, Enum):
    """Supported programming languages

    Inherits from str for JSON serialization compatibility.
    Defines the programming languages that can be executed in the system.
    Each language will need corresponding runtime environment support.
    """
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    RUBY = "ruby"
    # Add more languages as needed


class Project(BaseModel):
    """Represents a coding project workspace

    A project is the top-level container for code files and execution
    environment. It maintains metadata about the workspace and its owner.

    Attributes:
        id: Unique identifier for the project
        name: Display name of the project
        description: Optional detailed description
        language: Primary programming language for the project
        created_at: Timestamp of project creation
        updated_at: Timestamp of last modification
        owner_id: Identifier for the project owner
    """
    id: UUID                    # Unique identifier for the project
    name: str                   # Display name of the project
    description: Optional[str]  # Optional detailed description
    language: Language          # Primary programming language for the project
    created_at: datetime        # Timestamp of project creation
    updated_at: datetime        # Timestamp of last modification
    owner_id: str               # Identifier for the project owner


class File(BaseModel):
    """Represents a file in the project

    Tracks both file metadata and content. Files are always associated
    with a specific project and maintain their modification history.

    Attributes:
        id: Unique identifier for the file
        project_id: ID of the project this file belongs to
        path: Relative path within project
        content: File contents as text
        created_at: Timestamp of file creation
        updated_at: Timestamp of last modification

    Validators:
        path: Ensures path is not empty
        project_id: Validates and converts UUID strings to UUID objects
    """
    id: UUID                  # Unique identifier for the file
    project_id: UUID          # ID of the project this file belongs to
    path: str = Field(description="Relative path within project")
    content: str = Field(description="File contents")
    created_at: datetime      # Timestamp of file creation
    updated_at: datetime      # Timestamp of last modification

    model_config = {
        'strict': True,       # Enforce strict type checking
        'validate_assignment': True,
        'from_attributes': True
    }

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate the file path

        Args:
            v: Path string to validate

        Returns:
            str: The validated path

        Raises:
            ValueError: If path is empty or only whitespace
        """
        if not v.strip():
            raise ValueError("Path cannot be empty")
        return v

    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v):
        """Validate and convert project_id to UUID

        Args:
            v: Project ID to validate (str or UUID)

        Returns:
            UUID: The validated project ID

        Raises:
            ValueError: If value is not a valid UUID
        """
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc
        if not isinstance(v, UUID):
            raise ValueError("Must be UUID or valid UUID string")
        return v


class ExecutionResult(BaseModel):
    """Represents the result of code execution

    Tracks both the execution status and resource usage metrics.
    Used to monitor and report on code execution progress.

    Attributes:
        execution_id: Unique identifier for this execution
        project_id: ID of the project being executed
        status: Current execution status (QUEUED, RUNNING, etc.)
        stdout: Standard output from the execution
        stderr: Standard error output from the execution
        exit_code: Process exit code (None while running)
        started_at: When execution began
        completed_at: When execution finished (None while running)
        memory_usage: Peak memory usage in MB
        cpu_time: Total CPU time used in seconds
    """
    execution_id: UUID          # Unique identifier for this execution
    project_id: UUID           # ID of the project being executed
    status: ExecutionStatus    # Current execution status
    stdout: str                # Standard output from the execution
    stderr: str                # Standard error output from the execution
    exit_code: int | None      # Process exit code (None while running)
    started_at: datetime       # When execution began
    completed_at: datetime | None   # When execution finished (None while
                                    # noqa: E116               running)
    memory_usage: float        # Peak memory usage in MB
    cpu_time: float           # Total CPU time used in seconds

    model_config = {
        'strict': True,
        'validate_assignment': True,
    }


class ProjectStorage(ABC):
    """Interface for project persistence

    Defines the contract for storing and retrieving project data.
    Implementations might use databases, file systems, or other storage
    backends. All operations are async to support high concurrency.

    Implementation considerations:
        - Data consistency
        - Concurrent access
        - Error handling
        - Resource cleanup
    """

    @abstractmethod
    async def create_project(self, project: Project) -> Project:
        """Create a new project in storage.

        Args:
            project: The Project model to store. Should not have existing
                     storage ID.

        Returns:
            Project: The stored project with any storage-specific fields
                     populated.

        Raises:
            DuplicateError: If project with same name/owner already exists
            StorageError: If storage operation fails
        """

    @abstractmethod
    async def get_project(self, project_id: UUID) -> Project:
        """Retrieve a project by its ID.

        Args:
            project_id: UUID of the project to retrieve

        Returns:
            Project: The requested project

        Raises:
            NotFoundError: If project doesn't exist
            StorageError: If storage operation fails
        """

    @abstractmethod
    async def list_projects(self, owner_id: str) -> List[Project]:
        """List all projects owned by a specific user.

        Args:
            owner_id: ID of the project owner

        Returns:
            List[Project]: List of projects owned by the user

        Raises:
            StorageError: If storage operation fails
        """

    @abstractmethod
    async def delete_project(self, project_id: UUID) -> None:
        """Delete a project and all associated data.

        Args:
            project_id: UUID of the project to delete

        Raises:
            NotFoundError: If project doesn't exist
            StorageError: If storage operation fails
        """


class FileStorage(ABC):
    """Interface for file operations

    Handles the storage and retrieval of file contents and metadata.
    Should support efficient handling of multiple files within a project.
    All operations are async to support high concurrency.

    Implementation considerations:
        - File content storage strategy
        - Metadata management
        - Path handling and validation
        - Concurrent access
        - Resource cleanup
    """

    @abstractmethod
    async def save_file(self, file: File) -> File:
        """Save a new file or update an existing one.

        Args:
            file: The File model to save

        Returns:
            File: The saved file with any storage-specific fields populated

        Raises:
            NotFoundError: If project_id doesn't exist
            DuplicateError: If file path already exists in project
            StorageError: If storage operation fails
        """

    @abstractmethod
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

    @abstractmethod
    async def list_files(self, project_id: UUID) -> List[File]:
        """List all files in a project.

        Args:
            project_id: UUID of the project to list files from

        Returns:
            List[File]: List of files in the project

        Raises:
            NotFoundError: If project doesn't exist
            StorageError: If storage operation fails
        """

    @abstractmethod
    async def delete_file(self, file_id: UUID) -> None:
        """Delete a file from storage.

        Args:
            file_id: UUID of the file to delete

        Raises:
            NotFoundError: If file doesn't exist
            StorageError: If storage operation fails
        """


class CodeExecutor(ABC):
    """Interface for code execution

    Manages the lifecycle of code execution, from initiation to completion.
    Responsible for running code in appropriate isolation and capturing
    results. Should handle resource limits and execution timeouts.

    Implementation considerations:
        - Process isolation
        - Resource monitoring
        - Timeout enforcement
        - Output capture
        - Error handling
    """

    @abstractmethod
    async def execute(self,
                      project_id: UUID,
                      main_file: str) -> ExecutionResult:
        """Execute code from the project.

        Runs the specified main file in the context of the project,
        capturing all output and execution metrics.

        Args:
            project_id: UUID of the project containing the code
            main_file: Path to the entry point file relative to project root

        Returns:
            ExecutionResult: Results and metrics from the execution

        Raises:
            NotFoundError: If project or main_file doesn't exist
            ExecutionError: If execution fails to start or times out
            ResourceError: If execution exceeds resource limits
        """

    @abstractmethod
    async def terminate(self, execution_id: UUID) -> None:
        """Terminate a running execution.

        Forcefully stops the execution if it's still running.

        Args:
            execution_id: UUID of the execution to terminate

        Raises:
            NotFoundError: If execution_id doesn't exist
            ExecutionError: If termination fails
        """

    @abstractmethod
    async def get_status(self, execution_id: UUID) -> ExecutionResult:
        """Get current status and results of an execution.

        Args:
            execution_id: UUID of the execution to check

        Returns:
            ExecutionResult: Current status and any available results

        Raises:
            NotFoundError: If execution_id doesn't exist
        """


class RuntimeEnvironment(ABC):
    """Interface for managing isolated execution environments

    Handles the creation and management of isolated environments for code
    execution. Each environment should be isolated to prevent interference
    between projects and ensure security.

    Implementation considerations:
        - Virtual environment creation
        - Dependency management
        - Resource isolation
        - Environment cleanup
        - Security boundaries
        - Concurrent environment management
    """

    @abstractmethod
    async def create_environment(self, project_id: UUID) -> str:
        """Create an isolated environment for a project.

        Sets up a new environment with basic language runtime and tools.

        Args:
            project_id: UUID of the project needing an environment

        Returns:
            str: Unique identifier for the created environment

        Raises:
            EnvironmentError: If environment creation fails
            ResourceError: If system resources are insufficient
        """

    @abstractmethod
    async def install_dependencies(self,
                                   env_id: str,
                                   dependencies: List[str]) -> None:
        """Install required packages in the environment.

        Args:
            env_id: Environment identifier from create_environment
            dependencies: List of package specifications to install

        Raises:
            NotFoundError: If env_id doesn't exist
            DependencyError: If package installation fails
            SecurityError: If package is blocked by security policy
        """

    @abstractmethod
    async def cleanup_environment(self, env_id: str) -> None:
        """Cleanup and remove an environment.

        Args:
            env_id: Environment identifier to cleanup

        Raises:
            NotFoundError: If env_id doesn't exist
            EnvironmentError: If cleanup fails
        """
