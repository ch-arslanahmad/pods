from pathlib import Path
from sqlite3 import Row

from . import database as db

def create_db():
    conn = db.get_connection()
    schema = Path(__file__).parent / "schema.sql"
    conn.executescript(schema.read_text())
    conn.commit()
    conn.close()

def create_pod(pod_name: str, content: str, project: str | None, category: str) -> int:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(""" 
        INSERT INTO pods (pod_name, content, project, category)
        VALUES (?, ?, ?, ?)
    """, (pod_name, content, project, category))
    # timestamps handled by DB triggers

    conn.commit()
    pod_id : int = cursor.lastrowid if cursor.lastrowid else -1 # get the id of the newly created pod
    conn.close()
    return pod_id;

def get_pod(pod_id: int) -> dict | None:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pods WHERE id = ? AND deleted_at IS NULL", (pod_id,))
    row : Row = cursor.fetchone()

    conn.close()

    if row:
        return dict(row)
    else:
        return None


def list_pods(category: str | None = None, project: str | None = None) -> list[dict]:
    conn = db.get_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM pods WHERE deleted_at IS NULL" # only return non-deleted pods
    params: list = []

    if category:
        sql += " AND category = ?"
        params.append(category)
    if project:
        sql += " AND project = ?"
        params.append(project)

    sql += " ORDER BY created_at DESC" # sort by newest first

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_pod(pod_id: int, pod_name: str | None = None, content: str | None = None,
               project: str | None = None, category: str | None = None) -> dict | None:
    
    if not any([pod_name, content, project, category]):
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
    if project is not None:
        fields.append("project = ?")
        params.append(project)
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

    cursor.execute("UPDATE pods SET deleted_at = datetime('now', 'localtime') WHERE id = ? AND deleted_at IS NULL", (pod_id,)) # soft delete
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


def list_projects() -> list[str]:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT project FROM pods WHERE deleted_at IS NULL AND project IS NOT NULL ORDER BY project")
    rows = cursor.fetchall()
    conn.close()

    results = [r["project"] for r in rows]

    return results


def search_pods(query: str, project: str | None = None, category: str | None = None) -> list[dict]:
    conn = db.get_connection()
    cursor = conn.cursor()

    search_sql = """SELECT p.* FROM pods p 
JOIN pods_fts fts ON p.id = fts.ROWID
WHERE pods_fts MATCH ?
AND p.deleted_at IS NULL"""
    params: list = [query]

    if project:
        search_sql += " AND p.project = ?"
        params.append(project)
    if category:
        search_sql += " AND p.category = ?"
        params.append(category)

    cursor.execute(search_sql, params)
    rows = cursor.fetchall()
    conn.close()
    results : list[dict] = [dict(r) for r in rows]
    return results