"""Write one greeting row to Postgres and print the latest rows.

Connection settings come from the standard libpq environment variables, which
psycopg2 reads automatically: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
"""
import os

import psycopg2

name = os.environ.get("NAME", "world")

with psycopg2.connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS greetings (
                id         SERIAL PRIMARY KEY,
                name       TEXT        NOT NULL,
                message    TEXT        NOT NULL,
                source     TEXT        NOT NULL DEFAULT 'unknown',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            "INSERT INTO greetings (name, message, source) VALUES (%s, %s, %s)",
            (name, f"Hello, {name}!", "python"),
        )
        cur.execute(
            "SELECT id, source, name, message, created_at FROM greetings ORDER BY id DESC LIMIT 5"
        )
        for row in cur.fetchall():
            print(row, flush=True)
conn.close()
