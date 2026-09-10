-- single source of truth — edit this file, then rebuild the DB
CREATE TABLE IF NOT EXISTS pods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pod_name    TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '{}',   -- one JSON bag, not two
    project     TEXT,                          -- plain text label, not a FK (for now); NULL = standalone
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at  TEXT                           -- soft delete; never hard-delete rows
);

-- reserved for future multi-tag support (not yet wired to any tool)
CREATE TABLE IF NOT EXISTS pod_tags (
    pod_id  INTEGER NOT NULL REFERENCES pods(id), -- foreign key to pods.id
    tag     TEXT NOT NULL,
    PRIMARY KEY (pod_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_pods_category ON pods(category);
CREATE INDEX IF NOT EXISTS idx_pods_project  ON pods(project);

CREATE VIRTUAL TABLE IF NOT EXISTS pods_fts USING fts5(
    pod_name, content, category,project, -- search across every value
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

-- after insert: add new pod to the search index
CREATE TRIGGER IF NOT EXISTS pods_fts_insert AFTER INSERT ON pods BEGIN
    INSERT INTO pods_fts(rowid, pod_name, content, category, project) VALUES (new.id, new.pod_name, new.content, new.category, new.project);
END;

-- after update: always delete old FTS entry, re-add only if pod isn't soft-deleted
-- handles content updates, soft-delete, and undelete in one trigger
CREATE TRIGGER IF NOT EXISTS pods_fts_update AFTER UPDATE ON pods BEGIN
    INSERT INTO pods_fts(pods_fts, rowid, pod_name, content, category, project) VALUES ('delete', old.id, old.pod_name, old.content, old.category, old.project); -- delete old entry
    INSERT INTO pods_fts(rowid, pod_name, content, category, project)
    SELECT new.id, new.pod_name, new.content,new.category, new.project
    WHERE new.deleted_at IS NULL; -- insert new entry only if not soft-deleted
END;

-- rebuild FTS index for any existing rows (safety net for re-runs)
INSERT INTO pods_fts(pods_fts) VALUES('rebuild');
