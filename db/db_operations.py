import json
import sqlite3 as sql
from datetime import datetime
from pathlib import Path
from sqlite3 import Row

from . import database as db


# apply pending migrations (schema = migrations, not "create db")
def ensure_schema():
    from . import migrate

    migrate.run()


def backup(dest_dir: Path = Path("backups")) -> Path:
    dest_dir = db.DB_PATH.parent / dest_dir

    dest_dir.mkdir(parents=True, exist_ok=True)
    src = db.get_connection()

    # microseconds — two backups in the same second must never collide
    # (a colliding auto-backup would overwrite the file restore() is reading)
    dest = dest_dir / f"pods-{datetime.now():%Y-%m-%d_%H-%M-%S-%f}.db"

    dst = sql.connect(dest)
    src.backup(dst)
    dst.close()  # file-local conn; src is the shared cached conn
    return dest


def restore(backup_path: Path) -> None:
    if not backup_path.exists():
        raise sql.DatabaseError(f"backup file not found: {backup_path}")

    # pre-flight: never touch live db until backup proven good
    src = sql.connect(backup_path)
    try:
        status = src.execute("PRAGMA integrity_check").fetchone()[0]
        tables = src.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
    except sql.DatabaseError as e:
        src.close()
        raise sql.DatabaseError(f"not a valid sqlite backup: {backup_path}") from e
    if status != "ok":
        src.close()
        raise sql.DatabaseError(f"backup file corrupt: {backup_path} ({status})")
    if tables == 0:
        src.close()
        raise sql.DatabaseError(f"not a pods backup (no tables): {backup_path}")

    # snapshot current db before overwriting — insurance if restore goes wrong
    backup()

    dst = db.get_connection()
    src.backup(dst)
    src.close()  # file-local conn; dst is the shared cached conn


def create_pod(pod_name: str, content: str, project: str | None, category: str) -> int:
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
        INSERT INTO pods (pod_name, content, project, category)
        VALUES (?, ?, ?, ?)
    """,
            (pod_name, content, project, category),
        )
        # timestamps handled by DB triggers

        conn.commit()
    except sql.Error:
        conn.rollback()  # cached conn: don't leave a half-open txn behind
        raise
    pod_id: int = (
        cursor.lastrowid if cursor.lastrowid else -1
    )  # get the id of the newly created pod
    return pod_id


def get_pod(pod_id: int) -> dict | None:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pods WHERE id = ? AND deleted_at IS NULL", (pod_id,))
    row: Row = cursor.fetchone()

    if row:
        return dict(row)
    else:
        return None


def find_pods(
    query: str | None = None,
    category: str | None = None,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
    created_after: str | None = None,
    created_before: str | None = None,
) -> list[dict]:
    conn = db.get_connection()
    cursor = conn.cursor()

    if query:
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
        if created_after:
            search_sql += " AND date(p.created_at) >= date(?)"
            params.append(created_after)
        if created_before:
            search_sql += " AND date(p.created_at) <= date(?)"
            params.append(created_before)

        search_sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(search_sql, params)
    else:
        q = "SELECT * FROM pods WHERE deleted_at IS NULL"
        params: list = []

        if category:
            q += " AND category = ?"
            params.append(category)
        if project:
            q += " AND project = ?"
            params.append(project)
        if created_after:
            q += " AND date(created_at) >= date(?)"
            params.append(created_after)
        if created_before:
            q += " AND date(created_at) <= date(?)"
            params.append(created_before)

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(q, params)

    rows = cursor.fetchall()
    return [dict(r) for r in rows]


def update_pod(
    pod_id: int,
    pod_name: str | None = None,
    content: str | None = None,
    project: str | None = None,
    category: str | None = None,
) -> dict | None:

    if not any([pod_name, content, project, category]):
        print(f"Nothing to update for pod_id {pod_id}")
        return None  # nothing to update

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

    fields.append("updated_at = datetime('now', 'localtime')")

    params.append(pod_id)  # added ID for the WHERE clause

    try:
        cursor.execute(
            f"UPDATE pods SET {', '.join(fields)} WHERE id = ? AND deleted_at IS NULL",
            params,
        )
        conn.commit()
    except sql.Error:
        conn.rollback()
        raise

    return get_pod(pod_id)


def delete_pod(pod_id: int) -> bool:
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE pods SET deleted_at = datetime('now', 'localtime'), "
            "updated_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (pod_id,),
        )  # soft delete
        conn.commit()
    except sql.Error:
        conn.rollback()
        raise
    return cursor.rowcount > 0


def list_categories() -> list[str]:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT category FROM pods WHERE deleted_at IS NULL ORDER BY category"
    )
    rows = cursor.fetchall()

    results = [r["category"] for r in rows]

    return results


def list_projects() -> list[str]:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT project FROM pods WHERE deleted_at IS NULL AND project IS NOT NULL ORDER BY project"
    )
    rows = cursor.fetchall()

    results = [r["project"] for r in rows]

    return results


def seed_db() -> int:
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pods")
    if cursor.fetchone()[0] > 0:
        return 0

    seed_path = Path(__file__).parent / "seed.json"
    if not seed_path.exists():
        print("seed.json not found, skipping", file=__import__("sys").stderr)
        return 0

    pods = json.loads(seed_path.read_text())
    count = 0
    try:
        for pod in pods:
            cursor.execute(
                """
            INSERT INTO pods (pod_name, content, category, project)
            VALUES (?, ?, ?, ?)
        """,
                (pod["pod_name"], pod["content"], pod["category"], pod.get("project")),
            )
            count += 1
        conn.commit()
    except sql.Error:
        conn.rollback()
        raise
    return count
