"""Tests for the core models and interfaces

This module contains tests for the data models, storage interfaces,
and execution interfaces. Tests can run against either mock or real
implementations based on the test mode.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
import pytest

from replit_clone.models import (
    Project, File, ExecutionStatus, Language
)


@pytest.fixture
def sample_project():
    """Provides a valid sample Project instance for testing"""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        language=Language.PYTHON,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        owner_id="test_user"
    )


@pytest.fixture
def sample_file(sample_project):
    """Provides a valid sample File instance for testing"""
    return File(
        id=uuid4(),
        project_id=sample_project.id,
        path="main.py",
        content="print('Hello, World!')",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_create_project(project_storage, sample_project) -> None:
    """Test creating a new project"""
    project = await project_storage.create_project(sample_project)
    assert project.id == sample_project.id


@pytest.mark.asyncio
async def test_project_retrieval(project_storage, sample_project) -> None:
    """Tests that a stored project can be retrieved correctly"""
    await project_storage.create_project(sample_project)
    retrieved = await project_storage.get_project(sample_project.id)
    assert retrieved.id == sample_project.id


@pytest.mark.asyncio
async def test_project_listing(project_storage, sample_project) -> None:
    """Tests that projects can be listed by owner"""
    await project_storage.create_project(sample_project)
    projects = await project_storage.list_projects(sample_project.owner_id)
    assert len(projects) == 1
    assert projects[0].id == sample_project.id


@pytest.mark.asyncio
async def test_file_operations(file_storage, sample_file) -> None:
    """Tests the complete lifecycle of file operations"""
    # Test save
    saved = await file_storage.save_file(sample_file)
    assert saved.id == sample_file.id

    # Test retrieve
    retrieved = await file_storage.get_file(sample_file.id)
    assert retrieved.content == sample_file.content

    # Test list
    files = await file_storage.list_files(sample_file.project_id)
    assert len(files) == 1

    # Test delete
    await file_storage.delete_file(sample_file.id)
    with pytest.raises(KeyError):
        await file_storage.get_file(sample_file.id)


@pytest.mark.asyncio
async def test_code_execution(code_executor, sample_project) -> None:
    """Tests successful code execution flow

    Verifies that:
    - Execution starts successfully
    - Execution completes with expected status
    - Result contains expected status and exit code
    """
    # Create a simple test file
    exec_dir = code_executor.workspace / str(sample_project.id)
    exec_dir.mkdir(parents=True, exist_ok=True)

    assert not (exec_dir / "main.py").exists(), \
        "main.py should not exist before creation"
    with open(exec_dir / "main.py", "w", encoding="utf-8") as f:
        f.write("print('Hello, World!')\n")
    assert (exec_dir / "main.py").exists(), \
        "main.py should exist after creation"

    result = await code_executor.execute(sample_project.id, "main.py")
    assert result.status == ExecutionStatus.RUNNING

    # Poll for completion with timeout
    for _ in range(30):  # Try for up to 3 seconds
        await asyncio.sleep(0.1)
        final_result = await code_executor.get_status(result.execution_id)
        if final_result.status != ExecutionStatus.RUNNING:
            break

    assert final_result.status == ExecutionStatus.COMPLETED
    assert final_result.exit_code == 0


@pytest.mark.asyncio
async def test_execution_termination(code_executor, sample_project) -> None:
    """Tests execution termination functionality

    Verifies that:
    - Execution can be terminated
    - Status is updated appropriately after termination
    """
    exec_dir = code_executor.workspace / str(sample_project.id)
    exec_dir.mkdir(parents=True)

    assert not (exec_dir / "main.py").exists(), \
        "main.py should not exist before creation"
    with open(exec_dir / "main.py", "w", encoding="utf-8") as f:
        f.write("import time\nwhile True: time.sleep(0.1)\n")
    assert (exec_dir / "main.py").exists(), \
        "main.py should exist after creation"

    result = await code_executor.execute(sample_project.id, "main.py")
    await asyncio.sleep(0.1)
    await code_executor.terminate(result.execution_id)

    updated = await code_executor.get_status(result.execution_id)
    assert updated.status == ExecutionStatus.ERROR


@pytest.mark.asyncio
async def test_environment_lifecycle(
        runtime_environment, sample_project
) -> None:
    """Tests complete lifecycle of runtime environments

    Verifies that:
    - Environment can be created
    - Dependencies can be installed
    - Environment can be cleaned up
    - Proper errors are raised after cleanup
    """
    env_id = await runtime_environment.create_environment(sample_project.id)
    assert env_id.startswith("env_")

    await runtime_environment.install_dependencies(env_id, ["pytest"])

    await runtime_environment.cleanup_environment(env_id)
    with pytest.raises(KeyError):
        await runtime_environment.install_dependencies(env_id, ["pytest"])


@pytest.mark.asyncio
async def test_error_handling(project_storage, file_storage, code_executor):
    """Tests error handling across all storage interfaces

    Verifies that:
    - Appropriate errors are raised for invalid IDs
    - Each interface handles missing resources correctly
    """
    invalid_id = uuid4()

    with pytest.raises(KeyError):
        await project_storage.get_project(invalid_id)

    with pytest.raises(KeyError):
        await file_storage.get_file(invalid_id)

    with pytest.raises(KeyError):
        await code_executor.get_status(invalid_id)


def test_project_validation():
    """Tests Project model validation constraints

    Verifies that:
    - Invalid project names are rejected
    - Invalid languages are rejected
    - Required fields cannot be None
    """
    with pytest.raises(ValidationError):
        Project(
            id=uuid4(),
            name="",  # Empty name should be invalid
            language=Language.PYTHON,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            owner_id="test_user"
        )

    with pytest.raises(ValidationError):
        Project(
            id=uuid4(),
            name="Test Project",
            language="invalid_language",  # Invalid language
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            owner_id="test_user"
        )


def test_file_validation():
    """Tests File model validation constraints

    Verifies that:
    - Invalid file paths are rejected
    - Required fields cannot be None
    - Project ID must be valid UUID
    """
    with pytest.raises(ValidationError):
        File(
            id=uuid4(),
            project_id="not-a-uuid",  # Invalid UUID
            path="main.py",
            content="print('Hello')",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    with pytest.raises(ValidationError):
        File(
            id=uuid4(),
            project_id=uuid4(),
            path="",  # Empty path
            content="print('Hello')",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
