import sqlite3 as sql
import pathlib as path

DB_PATH = path.Path(__file__).parent / "pods.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True) # create the db directory if it doesn't exist


def get_connection() -> sql.Connection:
    conn = sql.connect(DB_PATH) # connect to the db, if doesn't exist, will be created
    conn.row_factory = sql.Row # default: tuples, we want dicts for access like row['column_name'] instead of row[0].
    conn.execute("PRAGMA journal_mode=WAL") # WAL required for Turso import, also better concurrent read performance
    return conn


def create_db():
    conn = get_connection()
    cursor = conn.cursor() # create the pods table if it doesn't exist

    create_db_query = """
CREATE TABLE IF NOT EXISTS pods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pod_name    TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '{}',   -- one JSON bag, not two
    project  TEXT,                          -- NULL = standalone
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TEXT NOT NULL DEFAULT (strftime('%d-%m-%Y,%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%d-%m-%Y,%H:%M:%S', 'now')),
    deleted_at  TEXT                           -- soft delete
);

CREATE TABLE IF NOT EXISTS pod_tags (
    pod_id  INTEGER NOT NULL REFERENCES pods(id), -- foreign key to pods.id
    tag     TEXT NOT NULL,
    PRIMARY KEY (pod_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_pods_category ON pods(category);
CREATE INDEX IF NOT EXISTS idx_pods_project  ON pods(project);

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

CREATE TRIGGER IF NOT EXISTS pods_fts_ai AFTER INSERT ON pods BEGIN
    INSERT INTO pods_fts(rowid, pod_name, content) VALUES (new.id, new.pod_name, new.content);
END;

CREATE TRIGGER IF NOT EXISTS pods_fts_ad AFTER DELETE ON pods BEGIN
    INSERT INTO pods_fts(pods_fts, rowid, pod_name, content) VALUES ('delete', old.id, old.pod_name, old.content);
END;

CREATE TRIGGER IF NOT EXISTS pods_fts_au AFTER UPDATE ON pods BEGIN
    INSERT INTO pods_fts(pods_fts, rowid, pod_name, content) VALUES ('delete', old.id, old.pod_name, old.content);
    INSERT INTO pods_fts(rowid, pod_name, content) VALUES (new.id, new.pod_name, new.content);
END;

"""


    cursor.executescript(create_db_query) # execute the query
    cursor.execute("INSERT INTO pods_fts(pods_fts) VALUES('rebuild')") # populate FTS index from existing data
    conn.commit() # commit the changes to the db
    conn.close() # close the connection


# this block only runs if you execute this file directly: python db.py
# it does NOT run if another file imports db.py
# useful for testing this file in isolation
if __name__ == "__main__":
    create_db()
    print("DB ready.")
