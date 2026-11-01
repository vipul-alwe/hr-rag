import os
import uuid
from contextlib import contextmanager

import psycopg2


# ==========================
# CONFIG
# ==========================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "ragdb"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "port": int(os.getenv("DB_PORT", "5432")),
}


# ==========================
# CONNECTION HANDLER
# ==========================

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(commit=False):
    with get_db_connection() as conn:
        cur = conn.cursor()

        try:
            yield cur

            if commit:
                conn.commit()

        finally:
            cur.close()


# ==========================
# TENANT RESOLUTION
# ==========================

def resolve_client_from_group(group_id: str):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT client_id
            FROM groups
            WHERE whatsapp_group_id = %s
            """,
            (group_id,)
        )

        result = cur.fetchone()

    return result[0] if result else None


# ==========================
# DOCUMENT INSERT
# ==========================

def insert_document(
    client_id: str,
    content: str,
    embedding_str: str,
    policy_name=None,
    section_title=None
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO documents
            (
                id,
                client_id,
                source,
                content,
                embedding,
                policy_name,
                section_title
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s::vector,
                %s,
                %s
            )
            """,
            (
                str(uuid.uuid4()),
                client_id,
                "api",
                content,
                embedding_str,
                policy_name,
                section_title
            )
        )


# ==========================
# VECTOR RETRIEVAL
# ==========================

def retrieve_similar(
    client_id: str,
    embedding_str: str,
    top_k: int = 20
):
    """
    Retrieve the most semantically similar documents.

    IMPORTANT:
    `score` is a similarity score where:

        1.0 = highly similar
        0.0 = not similar

    Higher score is therefore better.
    """

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                content,
                policy_name,
                section_title,
                (1 - (embedding <=> %s::vector)) AS similarity
            FROM documents
            WHERE client_id = %s
            ORDER BY similarity DESC
            LIMIT %s
            """,
            (
                embedding_str,
                client_id,
                top_k
            )
        )

        rows = cur.fetchall()

    results = []

    for row in rows:
        results.append(
            {
                "content": row[0],
                "policy_name": row[1],
                "section_title": row[2],
                "score": float(row[3]),
            }
        )

    return results