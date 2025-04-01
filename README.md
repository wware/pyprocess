# AI-assisted Python Development

I've been trying to develop a software development process that takes
advantage of AI assistance, the idea being to let the AI do the heavy
lifting, while I provide the context and direction. My hope is that
a sufficient set of foundational documentation can provide enough context
to prevent hallucinations and errors.

In an earlier experiment, I used SysML to describe a design, and realized
that I had bitten off more than I could chew, by trying a process that
was entirely language-agnostic. This time, I'll limit the scope to
Python, and think about generalizing the process later.

## Guardrails

What kinds of documents would be useful as guardrails? Plan to favor
Python-specific documentation and tools. These are not all necessary,
but within limitations of the language model's context window, you want
enough documentation to describe the system comprehensively.

- Sketch out the architecture using ABC classes and Pydantic models
- Describe the deployment environment
- Throw in a database schema
- If there is a web API, include an OpenAPI/Swagger spec
- If there is a CLI, include a docopt spec
- Black-box tests using either the CLI or the API
- Comprehensive unit and integration tests

## Starting over with the Todo app

To fill out the Pydantic/ABC idea, here is an example of a simple
system that can guide the LLM to fill out the architecture. Or we
can tell the LLM that this is the right way to start, and given a
natural language description of the system we actually want, the
LLM will write the Pydantic/ABC stuff for the target system, which
we can then review before proceeding.

## Example

Here is an example of a simple system. Here we describe an architecture using Pydantic and ABC
to get started, and the LLM will fill out the details.

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

<details>
<summary>Example design</summary>

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from abc import ABC, abstractmethod
from typing import List


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
    id: UUID               # Unique identifier for the todo item
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
        pass

    @abstractmethod
    async def get_todo(self, id: UUID) -> TodoItem:
        """Get a TodoItem by ID
        Args:
            id: UUID of the todo item to retrieve
        Returns:
            The requested TodoItem
        """
        pass

    @abstractmethod
    async def list_todos(self) -> List[TodoItem]:
        """List all TodoItems
        Returns:
            List of all TodoItems in storage
        """
        pass

    @abstractmethod
    async def update_todo(self,
                          id: UUID,
                          updates: TodoItemUpdates) -> TodoItem:
        """Update a TodoItem
        Args:
            id: UUID of the todo item to update
            updates: TodoItemUpdates containing the fields to update
        Returns:
            The updated TodoItem
        """
        pass

    @abstractmethod
    async def delete_todo(self, id: UUID) -> None:
        """Delete a TodoItem by ID
        Args:
            id: UUID of the todo item to delete
        """
        pass
```
</details>
