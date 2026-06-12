-- this is the souce of truth for the DB
-- this to be changed first then changed in the database.py or relevent files
CREATE TABLE IF NOT EXISTS pods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pod_name    TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '{}',   -- one JSON bag, not two
    project_id  TEXT,                          -- NULL = standalone
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT                           -- soft delete
);

CREATE TABLE IF NOT EXISTS pod_tags (
    pod_id  INTEGER NOT NULL REFERENCES pods(id), -- foreign key to pods.id
    tag     TEXT NOT NULL,
    PRIMARY KEY (pod_id, tag)
);

CREATE INDEX IF NOT EXISTS Iidx_pods_category ON pods(category);
CREATE INDEX IF NOT EXISTS idx_pods_project  ON pods(project_id);

CREATE VIRTUAL TABLE IF NOT EXISTS pods_fts USING fts5(
    pod_name, content,
    content='pods',
    content_rowid='id'
);

-- update the updated_at column to current timestamp when existing row is updated
CREATE TRIGGER IF NOT EXISTS set_pods_timestamp 
AFTER UPDATE ON pods
BEGIN
    UPDATE pods SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;
