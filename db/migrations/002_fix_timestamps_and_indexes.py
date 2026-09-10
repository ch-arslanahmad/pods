description = "Normalize timestamps to YYYY-MM-DD, rebuild FTS with category/project"


def upgrade(conn):
    # SQLite has no ALTER COLUMN, so we rebuild the table entirely.
    # Old default: strftime('%d-%m-%Y,%H:%M:%S','now') — DD-MM-YYYY
    # New default: datetime('now','localtime')          — YYYY-MM-DD HH:MM:SS
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pods_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pod_name    TEXT NOT NULL,
            content     TEXT NOT NULL DEFAULT '{}',
            project     TEXT,
            category    TEXT NOT NULL DEFAULT 'general',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            deleted_at  TEXT
        );

        INSERT INTO pods_new (id, pod_name, content, project, category, deleted_at)
        SELECT id, pod_name, content, project, category, deleted_at FROM pods;

        DROP TABLE pods;
        ALTER TABLE pods_new RENAME TO pods;

        CREATE INDEX IF NOT EXISTS idx_pods_category ON pods(category);
        CREATE INDEX IF NOT EXISTS idx_pods_project  ON pods(project);
    """)

    # Rebuild FTS to also index category and project (was only pod_name + content).
    # Then recreate triggers — they're gone after the DROP.
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pods_fts USING fts5(
            pod_name, content, category, project,
            content='pods',
            content_rowid='id'
        );

        INSERT INTO pods_fts(pods_fts) VALUES('rebuild');

        CREATE TRIGGER IF NOT EXISTS set_pods_timestamp
        AFTER UPDATE ON pods
        BEGIN
            UPDATE pods SET updated_at = datetime('now', 'localtime')
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS pods_fts_insert AFTER INSERT ON pods BEGIN
            INSERT INTO pods_fts(rowid, pod_name, content, category, project)
            VALUES (new.id, new.pod_name, new.content, new.category, new.project);
        END;

        CREATE TRIGGER IF NOT EXISTS pods_fts_update AFTER UPDATE ON pods BEGIN
            INSERT INTO pods_fts(pods_fts, rowid, pod_name, content, category, project)
            VALUES ('delete', old.id, old.pod_name, old.content, old.category, old.project);
            INSERT INTO pods_fts(rowid, pod_name, content, category, project)
            SELECT new.id, new.pod_name, new.content, new.category, new.project
            WHERE new.deleted_at IS NULL;
        END;
    """)
