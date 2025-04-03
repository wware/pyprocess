"""Test configuration and fixtures for the Replit Clone system

This module provides pytest fixtures and configuration for testing the system.
It supports different test modes to selectively use real implementations
or mocks for different components.

Test Modes:
    - ALL_MOCK: Use mocks for all components (default)
    - PROJECT_STORAGE: Test real project storage implementation
    - FILE_STORAGE: Test real file storage implementation
    - CODE_EXECUTOR: Test real code execution implementation
    - RUNTIME_ENV: Test real runtime environment implementation
"""

from enum import Enum
from typing import AsyncIterator

import pytest
import pytest_asyncio

from replit_clone.models import (
    ProjectStorage, FileStorage, CodeExecutor, RuntimeEnvironment
)
from replit_clone.implementations import (
    SQLiteProjectStorage,
    FileSystemStorage,
    DockerCodeExecutor,
    VenvRuntimeEnvironment
)
from replit_clone.tests.mocks import (
    MockStorage, MockProjectStorage, MockFileStorage, MockCodeExecutor,
    MockRuntimeEnvironment
)


class TestMode(str, Enum):
    """Specifies which implementation to test with real code

    Inherits from str for CLI argument parsing compatibility.
    Each mode determines which component uses real implementation
    while others use mocks.

    Values:
        ALL_MOCK: Use mocks for all components
        PROJECT_STORAGE: Test real project storage
        FILE_STORAGE: Test real file storage
        CODE_EXECUTOR: Test real code executor
        RUNTIME_ENV: Test real runtime environment
    """
    ALL_MOCK = "all-mock"
    PROJECT_STORAGE = "project-storage"
    FILE_STORAGE = "file-storage"
    CODE_EXECUTOR = "code-executor"
    RUNTIME_ENV = "runtime-env"


def pytest_addoption(parser):
    """Add command-line option to specify which implementation to test

    Args:
        parser: Pytest command line parser

    Adds:
        --test-mode: Option to select which component to test with real
                     implementation
    """
    parser.addoption(
        "--test-mode",
        action="store",
        default="all-mock",
        choices=[mode.value for mode in TestMode],
        help="Specify which implementation to test with real code"
    )


@pytest.fixture
def test_mode(request) -> TestMode:
    """Get the current test mode from command line option

    Args:
        request: Pytest request object containing command line options

    Returns:
        TestMode: The selected test mode
    """
    return TestMode(request.config.getoption("--test-mode"))


@pytest_asyncio.fixture
async def storage() -> MockStorage:
    """Base storage fixture for mocks

    Provides a shared mock storage instance that can be used
    by different mock implementations to maintain consistent state.

    Returns:
        MockStorage: Base storage instance for mocks
    """
    return MockStorage()


@pytest_asyncio.fixture
async def project_storage(
        test_mode: TestMode,
        storage: MockStorage
) -> AsyncIterator[ProjectStorage]:
    """Provides project storage implementation based on test mode

    Args:
        test_mode: Current test mode
        storage: Base storage for mocks

    Yields:
        ProjectStorage: Real SQLite implementation if in PROJECT_STORAGE mode,
                       otherwise a mock implementation
    """
    if test_mode == TestMode.PROJECT_STORAGE:
        real_storage = SQLiteProjectStorage(":memory:")
        await real_storage.initialize()
        try:
            yield real_storage
        finally:
            await real_storage.cleanup()
    else:
        yield MockProjectStorage(storage)


@pytest_asyncio.fixture
async def file_storage(
        test_mode: TestMode,
        storage: MockStorage
) -> AsyncIterator[FileStorage]:
    """Provides file storage implementation based on test mode

    Args:
        test_mode: Current test mode
        storage: Base storage for mocks

    Yields:
        FileStorage: Real filesystem implementation if in FILE_STORAGE mode,
                    otherwise a mock implementation
    """
    if test_mode == TestMode.FILE_STORAGE:
        real_storage = FileSystemStorage("/tmp/test_workspace")
        await real_storage.initialize()
        try:
            yield real_storage
        finally:
            await real_storage.cleanup()
    else:
        yield MockFileStorage(storage)


@pytest_asyncio.fixture
async def code_executor(
        test_mode: TestMode,
        storage: MockStorage
) -> AsyncIterator[CodeExecutor]:
    """Provides code executor implementation based on test mode

    Args:
        test_mode: Current test mode
        storage: Base storage for mocks

    Yields:
        CodeExecutor: Real Docker implementation if in CODE_EXECUTOR mode,
                     otherwise a mock implementation
    """
    if test_mode == TestMode.CODE_EXECUTOR:
        executor = DockerCodeExecutor()
        await executor.initialize()
        try:
            yield executor
        finally:
            await executor.cleanup()
    else:
        yield MockCodeExecutor(storage)


@pytest_asyncio.fixture
async def runtime_environment(
        test_mode: TestMode,
        storage: MockStorage
) -> AsyncIterator[RuntimeEnvironment]:
    """Provides runtime environment implementation based on test mode

    Args:
        test_mode: Current test mode
        storage: Base storage for mocks

    Yields:
        RuntimeEnvironment: Real venv implementation if in RUNTIME_ENV mode,
                          otherwise a mock implementation
    """
    if test_mode == TestMode.RUNTIME_ENV:
        env = VenvRuntimeEnvironment()
        await env.initialize()
        try:
            yield env
        finally:
            await env.cleanup()
    else:
        yield MockRuntimeEnvironment(storage)
