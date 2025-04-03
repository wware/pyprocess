"""Mock implementations for testing"""

from dataclasses import dataclass, field
from typing import Dict, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pathlib import Path

from replit_clone.models import (
    Project, File, ExecutionResult, ExecutionStatus,
    ProjectStorage, FileStorage, CodeExecutor, RuntimeEnvironment
)


@dataclass
class MockStorage:
    """Helper class to store data in memory for testing"""
    projects: Dict[UUID, Project] = field(default_factory=dict)
    files: Dict[UUID, File] = field(default_factory=dict)
    executions: Dict[UUID, ExecutionResult] = field(default_factory=dict)
    environments: Dict[str, str] = field(default_factory=dict)


class MockProjectStorage(ProjectStorage):
    """Mock implementation of ProjectStorage for testing"""
    def __init__(self, storage: MockStorage):
        self.storage = storage

    async def create_project(self, project: Project) -> Project:
        if project.id in self.storage.projects:
            raise ValueError("Project already exists")
        self.storage.projects[project.id] = project
        return project

    async def get_project(self, project_id: UUID) -> Project:
        if project_id not in self.storage.projects:
            raise KeyError("Project not found")
        return self.storage.projects[project_id]

    async def list_projects(self, owner_id: str) -> List[Project]:
        return [p for p in self.storage.projects.values()
                if p.owner_id == owner_id]

    async def delete_project(self, project_id: UUID) -> None:
        if project_id not in self.storage.projects:
            raise KeyError("Project not found")
        del self.storage.projects[project_id]


class MockFileStorage(FileStorage):
    """Mock implementation of FileStorage interface

    Provides in-memory storage for testing without filesystem dependencies.
    Uses the shared MockStorage instance to maintain state.
    """
    def __init__(self, storage: MockStorage):
        self.storage = storage

    async def save_file(self, file: File) -> File:
        self.storage.files[file.id] = file
        return file

    async def get_file(self, file_id: UUID) -> File:
        """Get file by ID from mock storage"""
        if file_id not in self.storage.files:
            raise KeyError("File not found")
        return self.storage.files[file_id]

    async def list_files(self, project_id: UUID) -> List[File]:
        return [f for f in self.storage.files.values()
                if f.project_id == project_id]

    async def delete_file(self, file_id: UUID) -> None:
        """Delete file by ID from mock storage"""
        if file_id not in self.storage.files:
            raise KeyError("File not found")
        del self.storage.files[file_id]


class MockCodeExecutor(CodeExecutor):
    """Mock implementation of CodeExecutor for testing"""

    def __init__(self, storage: MockStorage):
        """Initialize with mock storage and workspace path"""
        self.storage = storage
        self.workspace = Path("/tmp/mock_workspace")

    async def execute(
            self,
            project_id: UUID,
            _: str
    ) -> ExecutionResult:
        """Mock execution starts in RUNNING state"""
        execution_id = uuid4()
        self.storage.executions[execution_id] = {
            'project_id': project_id,
            'status': ExecutionStatus.RUNNING,
            'exit_code': None,
            'stdout': '',
            'stderr': '',
            'started_at': datetime.now(timezone.utc),
            'completed_at': None
        }
        return ExecutionResult(
            execution_id=execution_id,
            project_id=project_id,
            status=ExecutionStatus.RUNNING,
            stdout='',
            stderr='',
            exit_code=None,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            memory_usage=0.0,
            cpu_time=0.0
        )

    async def terminate(self, execution_id: UUID) -> None:
        """Mock termination always succeeds"""
        if execution_id not in self.storage.executions:
            raise KeyError(f"Execution {execution_id} not found")
        self.storage.executions[execution_id]['status'] = ExecutionStatus.ERROR

    async def get_status(self, execution_id: UUID) -> ExecutionResult:
        """Return mock execution status"""
        if execution_id not in self.storage.executions:
            raise KeyError(f"Execution {execution_id} not found")

        exec_data = self.storage.executions[execution_id]

        if exec_data['status'] == ExecutionStatus.RUNNING:
            exec_data.update({
                'status': ExecutionStatus.COMPLETED,
                'exit_code': 0,
                'stdout': 'Mock output',
                'completed_at': datetime.now(timezone.utc)
            })

        return ExecutionResult(
            execution_id=execution_id,
            project_id=exec_data['project_id'],
            status=exec_data['status'],
            stdout=exec_data.get('stdout', ''),
            stderr=exec_data.get('stderr', ''),
            exit_code=exec_data.get('exit_code'),
            started_at=exec_data['started_at'],
            completed_at=exec_data.get('completed_at'),
            memory_usage=0.0,
            cpu_time=0.0
        )


class MockRuntimeEnvironment(RuntimeEnvironment):
    """Mock implementation of RuntimeEnvironment interface

    Simulates virtual environment management without creating real
    environments. Uses the shared MockStorage instance to track environments.
    """
    def __init__(self, storage: MockStorage):
        self.storage = storage

    async def create_environment(self, project_id: UUID) -> str:
        env_id = f"env_{project_id}"
        self.storage.environments[env_id] = str(project_id)
        return env_id

    async def install_dependencies(
            self, env_id: str, dependencies: List[str]
    ) -> None:
        if env_id not in self.storage.environments:
            raise KeyError("Environment not found")

    async def cleanup_environment(self, env_id: str) -> None:
        if env_id not in self.storage.environments:
            raise KeyError("Environment not found")
        del self.storage.environments[env_id]
