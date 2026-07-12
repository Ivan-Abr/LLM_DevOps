CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_base (
    id          SERIAL PRIMARY KEY,
    category    TEXT NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(768),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_base_embedding_idx
    ON knowledge_base USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS knowledge_base_category_idx
    ON knowledge_base (category);