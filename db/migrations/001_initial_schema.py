from pathlib import Path

description = "Initial schema — creates pods, pod_tags, indexes, FTS, triggers"


def upgrade(conn):
    schema = Path(__file__).parent.parent / "schema.sql"
    conn.executescript(schema.read_text())
    conn.commit()
