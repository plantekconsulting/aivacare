"""Postgres access: app tables, pgvector knowledge index, audit log."""
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .config import settings

pool: AsyncConnectionPool | None = None

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kb_chunks (
  id SERIAL PRIMARY KEY,
  doc_id TEXT NOT NULL,
  title TEXT NOT NULL,
  section TEXT NOT NULL,
  audience TEXT NOT NULL,
  version TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384) NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || section || ' ' || content)) STORED
);
CREATE INDEX IF NOT EXISTS kb_chunks_tsv ON kb_chunks USING gin(tsv);

CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY,
  patient_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uploads (
  id SERIAL PRIMARY KEY,
  patient_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  media_type TEXT NOT NULL,
  data BYTEA NOT NULL,
  extraction JSONB,
  status TEXT NOT NULL DEFAULT 'uploaded',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  detail JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def init_db() -> None:
    global pool
    pool = AsyncConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    )
    await pool.open()
    async with pool.connection() as conn:
        await conn.execute(SCHEMA)


async def close_db() -> None:
    if pool:
        await pool.close()


async def fetch(sql: str, *args) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(sql, args)
        return await cur.fetchall() if cur.description else []


async def execute(sql: str, *args) -> None:
    async with pool.connection() as conn:
        await conn.execute(sql, args)


async def audit(actor: str, action: str, detail: dict | None = None) -> None:
    await execute(
        "INSERT INTO audit_log (actor, action, detail) VALUES (%s, %s, %s)", actor, action, Jsonb(detail or {})
    )
