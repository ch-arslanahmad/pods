description = "Drop set_pods_timestamp trigger (upstream FTS5 corruption bug); set updated_at in SQL"


def upgrade(conn):
    conn.executescript(
        "DROP TRIGGER IF EXISTS set_pods_timestamp;"
        "INSERT INTO pods_fts(pods_fts) VALUES('rebuild');"
    )
    conn.commit()
