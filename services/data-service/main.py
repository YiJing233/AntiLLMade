# Data Service - 统一数据访问层
# 独立的数据持久化服务，支持多数据库

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, AsyncIterator
import os
import asyncpg

# 配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/antillmade")
POOL_SIZE = 10

pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=POOL_SIZE,
        command_timeout=60,
    )
    print(f"Data Service started, DATABASE_URL={DATABASE_URL}")
    yield
    await pool.close()


app = FastAPI(title="Data Access Service", lifespan=lifespan)


# ========== Models ==========

class Source(BaseModel):
    id: int
    url: str
    title: str
    category: str


class Entry(BaseModel):
    id: int
    source_id: int
    title: str
    link: str
    published_at: datetime
    summary: str
    content: str
    unread: bool


class SourceCreate(BaseModel):
    url: str
    title: str
    category: str = "默认"


# ========== CRUD Operations ==========

async def get_conn() -> asyncpg.Connection:
    """获取数据库连接"""
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return await pool.acquire()


@app.get("/health")
def health():
    return {"status": "ok", "service": "data"}


@app.get("/sources", response_model=List[Source])
async def list_sources():
    async with get_conn() as conn:
        rows = await conn.fetch(
            "SELECT id, url, title, category FROM sources ORDER BY id DESC"
        )
        return [dict(row) for row in rows]


@app.post("/sources", response_model=Source)
async def create_source(payload: SourceCreate):
    async with get_conn() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO sources (url, title, category)
                VALUES ($1, $2, $3)
                ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title, category = EXCLUDED.category
                RETURNING id, url, title, category
                """,
                payload.url, payload.title, payload.category,
            )
            return dict(row)
        except asyncpg.UniqueViolationError:
            # 如果 URL 已存在，获取它
            row = await conn.fetchrow(
                "SELECT id, url, title, category FROM sources WHERE url = $1",
                payload.url,
            )
            return dict(row)


@app.delete("/sources/{source_id}")
async def delete_source(source_id: int):
    async with get_conn() as conn:
        await conn.execute("DELETE FROM sources WHERE id = $1", source_id)
    return {"status": "deleted"}


@app.get("/entries", response_model=List[Entry])
async def list_entries(date: Optional[str] = None, limit: int = 100):
    async with get_conn() as conn:
        if date:
            rows = await conn.fetch(
                """
                SELECT * FROM entries
                WHERE date(published_at) = date($1)
                ORDER BY published_at DESC
                LIMIT $2
                """,
                date, limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM entries ORDER BY published_at DESC LIMIT $1",
                limit,
            )
        return [dict(row) for row in rows]


@app.post("/entries")
async def create_entry(entry: Entry):
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO entries (source_id, title, link, published_at, summary, content, unread)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (source_id, link) DO NOTHING
            RETURNING *
            """,
            entry.source_id, entry.title, entry.link, entry.published_at,
            entry.summary, entry.content, entry.unread,
        )
        return dict(row) if row else {"status": "skipped"}


@app.get("/entries/{entry_id}")
async def get_entry(entry_id: int):
    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT * FROM entries WHERE id = $1", entry_id)
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        return dict(row)


@app.patch("/entries/{entry_id}/read")
async def mark_entry_read(entry_id: int):
    async with get_conn() as conn:
        await conn.execute("UPDATE entries SET unread = FALSE WHERE id = $1", entry_id)
    return {"status": "read"}


# ========== Statistics ==========

@app.get("/stats/sources")
async def source_stats():
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.url, s.title, s.category,
                   COUNT(e.id) FILTER (WHERE e.unread) as unread_count,
                   MAX(e.published_at) as latest_entry_at
            FROM sources s
            LEFT JOIN entries e ON s.id = e.source_id
            GROUP BY s.id
            ORDER BY s.id DESC
            """
        )
        return [dict(row) for row in rows]
