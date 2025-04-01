"""Example preliminary architecture using Pydantic and ABC

This module demonstrates some best practices for creating a well-structured,
type-safe application using modern Python features.

    - Strong typing with type hints and validation
        - Pydantic models for data validation
        - UUID for unique identifiers
        - Proper enum implementation
        - Comprehensive use of typing module

    - Clean architecture principles
        - Interface-based design using ABC
        - Clear separation of concerns
        - Abstract storage layer supporting multiple implementations
          and dependency injection for testing
        - Async operations for scalability

    - Python best practices
        - PEP 8 compliant naming conventions
        - Well-organized imports
        - Proper class hierarchy
        - Comprehensive documentation

    - Data validation and safety
        - Pydantic BaseModel inheritance
        - Strict type checking
        - Optional fields for partial updates
        - Enum-based status management
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class Status(str, Enum):
    """Status enum for TodoItem

    Inherits from str to ensure JSON serialization compatibility
    Defines the possible states of a todo item
    """
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TodoItem(BaseModel):
    """
    Main Todo item model that defines the structure of a todo entry
    Inherits from Pydantic BaseModel for automatic data validation
    """
    item_id: UUID          # Unique identifier for the todo item
    title: str             # Title of the todo item
    description: str       # Detailed description of the todo item
    status: Status         # Current status of the todo item
    created_at: datetime   # Timestamp when the item was created
    updated_at: datetime   # Timestamp when the item was last updated


class TodoItemUpdates(BaseModel):
    """
    Model for updating TodoItem
    All fields are Optional to allow partial updates
    """
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Status] = None


class TodoStorage(ABC):
    """
    Abstract base class defining the interface for todo storage operations
    Implementations of this class can store todos in different backends
    (database, file, etc.)
    """

    @abstractmethod
    async def create_todo(self, item: TodoItem) -> TodoItem:
        """Create a new TodoItem in storage
        Args:
            item: The TodoItem to create
        Returns:
            The created TodoItem
        """

    @abstractmethod
    async def get_todo(self, item_id: UUID) -> TodoItem:
        """Get a TodoItem by ID
        Args:
            item_id: UUID of the todo item to retrieve
        Returns:
            The requested TodoItem
        """

    @abstractmethod
    async def list_todos(self) -> List[TodoItem]:
        """List all TodoItems
        Returns:
            List of all TodoItems in storage
        """

    @abstractmethod
    async def update_todo(
            self,
            item_id: UUID,
            updates: TodoItemUpdates
    ) -> TodoItem:
        """Update a TodoItem
        Args:
            item_id: UUID of the todo item to update
            updates: TodoItemUpdates containing the fields to update
        Returns:
            The updated TodoItem
        """

    @abstractmethod
    async def delete_todo(self, item_id: UUID) -> None:
        """Delete a TodoItem by ID
        Args:
            item_id: UUID of the todo item to delete
        """
