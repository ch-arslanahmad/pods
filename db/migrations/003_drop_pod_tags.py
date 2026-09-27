description = "Drop unused pod_tags table (never wired to any tool)"


def upgrade(conn):
    conn.executescript("DROP TABLE IF EXISTS pod_tags;")
    conn.commit()
