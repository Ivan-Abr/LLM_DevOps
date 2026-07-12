import os
import psycopg2
from pgvector.psycopg2 import register_vector
import ollama

DB_DSN = os.environ.get(
    "RAG_DB_DSN",
    "dbname=devops_rag user=postgres password=postgres host=localhost port=5433",
)
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "nomic-embed-text")

def embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]

def connect():
    conn = psycopg2.connect(DB_DSN)
    register_vector(conn)  # allows passing python list directly as VECTOR
    return conn

def check_connection() -> bool:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False

def add_document(category: str, title: str, content: str) -> int:
    vec = embed(content)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_base (category, title, content, embedding) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (category, title, content, vec),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return new_id


def search(query: str, category: str | None = None, k: int = 2) -> list[dict]:
    vec = embed(query)

    sql = "SELECT title, content, embedding <=> %s AS distance FROM knowledge_base"
    params: list = [vec]

    if category:
        sql += " WHERE category = %s"
        params.append(category)

    sql += " ORDER BY distance LIMIT %s"
    params.append(k)

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [{"title": r[0], "content": r[1], "distance": float(r[2])} for r in rows]


def count_documents(category: str | None = None) -> int:
    """Return the number of documents stored, optionally filtered by category."""
    sql = "SELECT COUNT(*) FROM knowledge_base"
    params: list = []
    if category:
        sql += " WHERE category = %s"
        params.append(category)

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]
