-- Create the todos table to store TodoItem entities
CREATE TABLE todos (
    id TEXT PRIMARY KEY,           -- UUID stored as text
    title TEXT NOT NULL,           -- Required title
    description TEXT NOT NULL,     -- Required description
    status TEXT NOT NULL           -- Matches Status enum
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on status to optimize queries filtering by status
CREATE INDEX idx_todos_status ON todos(status);

-- Create trigger to automatically update the updated_at timestamp
CREATE TRIGGER update_todos_timestamp 
    AFTER UPDATE ON todos
    FOR EACH ROW
BEGIN
    UPDATE todos SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
