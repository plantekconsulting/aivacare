"""Knowledge RAG: clinician-approved content -> chunks -> local embeddings -> pgvector hybrid search."""
import asyncio
import re
from functools import lru_cache

import yaml
from pgvector.psycopg import register_vector_async

from . import db
from .config import APP_DIR

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
MIN_SIMILARITY = 0.55  # below this, the assistant says it has no approved information


@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(EMBED_MODEL)


def _embed_sync(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _embedder().embed(texts)]


async def embed(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(_embed_sync, texts)


def load_documents() -> list[dict]:
    chunks = []
    for path in sorted((APP_DIR / "content").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front)
        for section in re.split(r"^## ", body, flags=re.MULTILINE)[1:]:
            heading, _, text = section.partition("\n")
            chunks.append({
                "doc_id": path.stem, "title": meta["title"], "section": heading.strip(),
                "audience": meta["audience"], "version": str(meta["version"]),
                "approved_by": meta["approved_by"], "content": text.strip(),
            })
    return chunks


async def ingest() -> int:
    chunks = load_documents()
    vectors = await embed([f"{c['title']} - {c['section']}: {c['content']}" for c in chunks])
    async with db.pool.connection() as conn:
        await register_vector_async(conn)
        await conn.execute("TRUNCATE kb_chunks")
        async with conn.cursor() as cur:
            await cur.executemany(
                "INSERT INTO kb_chunks (doc_id, title, section, audience, version, approved_by, content, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [(c["doc_id"], c["title"], c["section"], c["audience"], c["version"], c["approved_by"], c["content"], v)
                 for c, v in zip(chunks, vectors)],
            )
    return len(chunks)


async def search(query: str, audiences: list[str], k: int = 4) -> list[dict]:
    """Hybrid search (vector + full text, reciprocal rank fusion) restricted to the given audiences."""
    [qv] = await embed([query])
    async with db.pool.connection() as conn:
        await register_vector_async(conn)
        cur = await conn.execute(
            """
            WITH v AS (
              SELECT id, 1 - (embedding <=> %(qv)s::vector) AS sim,
                     row_number() OVER (ORDER BY embedding <=> %(qv)s::vector) AS r
              FROM kb_chunks WHERE audience = ANY(%(aud)s) ORDER BY embedding <=> %(qv)s::vector LIMIT 10
            ), t AS (
              SELECT id, row_number() OVER (ORDER BY ts_rank(tsv, q) DESC) AS r
              FROM kb_chunks, plainto_tsquery('english', %(q)s) q
              WHERE audience = ANY(%(aud)s) AND tsv @@ q LIMIT 10
            )
            SELECT c.id, c.doc_id, c.title, c.section, c.version, c.approved_by, c.content, v.sim,
                   COALESCE(1.0 / (60 + v.r), 0) + COALESCE(1.0 / (60 + t.r), 0) AS score
            FROM kb_chunks c LEFT JOIN v ON v.id = c.id LEFT JOIN t ON t.id = c.id
            WHERE v.id IS NOT NULL OR t.id IS NOT NULL
            ORDER BY score DESC LIMIT %(k)s
            """,
            {"qv": qv, "aud": audiences, "q": query, "k": k},
        )
        rows = await cur.fetchall()
    best = max((r["sim"] or 0 for r in rows), default=0)
    if best < MIN_SIMILARITY:
        return []
    return [r for r in rows if (r["sim"] or 0) >= MIN_SIMILARITY - 0.1]
