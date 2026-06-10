from sqlite3 import Row

from . import database as db

def create_db():
    conn = db.get_connection()
    cursor = conn.cursor() # create the pods table if it doesn't exist

    create_db_query = """
CREATE TABLE IF NOT EXISTS pods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pod_name    TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '{}',   -- one JSON bag, not two
    project_id  TEXT,                          -- NULL = standalone
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TEXT NOT NULL DEFAULT (strftime('%d-%m-%Y,%H:%M:%S', 'now')),
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

-- Triggers to keep the updated_at column updated automatically
CREATE TRIGGER IF NOT EXISTS update_pods_timestamp 
AFTER UPDATE ON pods
BEGIN
    UPDATE pods SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

"""


    cursor.executescript(create_db_query) # execute the query
    conn.commit() # commit the changes to the db
    conn.close() # close the connection


def create_pod(pod_name: str, content: str, project_id: str | None, category: str) -> int:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(""" 
        INSERT INTO pods (pod_name, content, project_id, category)
        VALUES (?, ?, ?, ?)
    """, (pod_name, content, project_id, category))
    # timestamps handled by DB triggers

    conn.commit()
    pod_id : int = cursor.lastrowid if cursor.lastrowid else -1 # get the id of the newly created pod
    conn.close()
    return pod_id;

def get_pod(pod_id: int) -> dict | None:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pods WHERE id = ?", (pod_id,))
    row : Row = cursor.fetchone()

    conn.close()

    if row:
        return dict(row)
    else:
        return None


def list_pods(category: str | None = None, project_id: str | None = None) -> list[dict]:
    conn = db.get_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM pods WHERE deleted_at IS NULL" # only return non-deleted pods
    params: list = []

    if category:
        sql += " AND category = ?"
        params.append(category)
    if project_id:
        sql += " AND project_id = ?"
        params.append(project_id)

    sql += " ORDER BY created_at DESC" # sort by newest first

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_pod(pod_id: int, pod_name: str | None = None, content: str | None = None,
               project_id: str | None = None, category: str | None = None) -> dict | None:
    
    if not any([pod_name, content, project_id, category]):
        print(f"Nothing to update for pod_id {pod_id}");
        return None # nothing to update

    conn = db.get_connection()
    cursor = conn.cursor()

    fields = []
    params: list = []

    if pod_name is not None:
        fields.append("pod_name = ?")
        params.append(pod_name)
    if content is not None:
        fields.append("content = ?")
        params.append(content)
    if project_id is not None:
        fields.append("project_id = ?")
        params.append(project_id)
    if category is not None:
        fields.append("category = ?")
        params.append(category)

    # updated_at handled by DB trigger

    params.append(pod_id) # added ID for the WHERE clause

    cursor.execute(f"UPDATE pods SET {', '.join(fields)} WHERE id = ? AND deleted_at IS NULL", params)
    conn.commit()
    conn.close()

    return get_pod(pod_id)


def delete_pod(pod_id: int) -> bool:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE pods SET deleted_at = 1 WHERE id = ? AND deleted_at IS NULL", (pod_id,)) # soft delete
    # deleted_at timestamp handled by DB trigger
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def list_categories() -> list[str]:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT category FROM pods WHERE deleted_at IS NULL ORDER BY category")
    rows = cursor.fetchall()
    conn.close()

    results = [r["category"] for r in rows]

    return results


def search_pods(query: str) -> list[dict]:
    conn = db.get_connection()
    cursor = conn.cursor()

    search_sql = """SELECT p.* FROM pods p 
JOIN pods_fts fts ON p.id = fts.ROWID
WHERE pods_fts MATCH ? -- it matches the value
AND p.deleted_at IS NULL -- not deleted"""

    cursor.execute(search_sql, (query,))
    rows = cursor.fetchall()
    conn.close()
    results : list[dict] = [dict(r) for r in rows]
    return results