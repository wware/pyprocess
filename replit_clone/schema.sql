-- Schema for SQLite database implementation of Replit Clone storage

-- Projects table stores basic project metadata
CREATE TABLE projects (
    id TEXT PRIMARY KEY,              -- UUID stored as text
    name TEXT NOT NULL,               -- Project display name
    description TEXT,                 -- Optional description
    language TEXT NOT NULL            -- Matches Language enum
        CHECK (language IN ('python', 'javascript', 'ruby')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    owner_id TEXT NOT NULL,           -- User identifier
    UNIQUE (owner_id, name)           -- Prevent duplicate project names per user
);

-- Files table stores file metadata and content
CREATE TABLE files (
    id TEXT PRIMARY KEY,              -- UUID stored as text
    project_id TEXT NOT NULL,         -- Foreign key to projects
    path TEXT NOT NULL,               -- Relative path within project
    content TEXT NOT NULL,            -- File contents
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id, path)         -- Prevent duplicate paths within project
);

-- Executions table tracks code execution attempts
CREATE TABLE executions (
    id TEXT PRIMARY KEY,              -- UUID stored as text
    project_id TEXT NOT NULL,         -- Foreign key to projects
    status TEXT NOT NULL              -- Matches ExecutionStatus enum
        CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'ERROR')),
    stdout TEXT NOT NULL DEFAULT '',  -- Captured standard output
    stderr TEXT NOT NULL DEFAULT '',  -- Captured standard error
    exit_code INTEGER,                -- Process exit code (NULL if not completed)
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,           -- NULL if not completed
    memory_usage REAL,                -- Peak memory usage in MB
    cpu_time REAL,                    -- Total CPU time in seconds
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Environments table tracks runtime environments
CREATE TABLE environments (
    id TEXT PRIMARY KEY,              -- Environment identifier
    project_id TEXT NOT NULL,         -- Foreign key to projects
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Create indexes for common queries
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_files_project ON files(project_id);
CREATE INDEX idx_executions_project ON executions(project_id);
CREATE INDEX idx_executions_status ON executions(status);

-- Create triggers for updated_at timestamps
CREATE TRIGGER update_project_timestamp 
    AFTER UPDATE ON projects
    FOR EACH ROW
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER update_file_timestamp 
    AFTER UPDATE ON files
    FOR EACH ROW
BEGIN
    UPDATE files SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END; 