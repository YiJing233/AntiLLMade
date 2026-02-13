# Source Management Service
# 独立的订阅源管理微服务

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime
import sqlite3
import os

DB_PATH = os.getenv("SOURCE_DB_PATH", "./sources.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"Source Service started, DB_PATH={DB_PATH}")
    yield

app = FastAPI(title="Source Management Service", lifespan=lifespan)


class SourceCreate(BaseModel):
    url: str
    title: str
    category: str = "默认"


class SourceResponse(BaseModel):
    id: int
    url: str
    title: str
    category: str


class SourceMeta(BaseModel):
    id: int
    url: str
    title: str
    category: str
    unread_count: int
    has_unread: bool
    latest_entry_at: str | None


def init_db():
    """初始化数据库"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_conn():
    """数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/health")
def health():
    return {"status": "ok", "service": "source"}


@app.get("/sources", response_model=list[SourceResponse])
def list_sources():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, url, title, category FROM sources ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/sources/meta", response_model=list[SourceMeta])
def list_sources_with_meta():
    """获取订阅源及统计信息"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                s.id, s.url, s.title, s.category,
                COUNT(CASE WHEN e.unread = 1 THEN 1 END) AS unread_count,
                MAX(e.published_at) AS latest_entry_at
            FROM sources s
            LEFT JOIN entries e ON s.id = e.source_id
            GROUP BY s.id
            ORDER BY s.id DESC
        """).fetchall()

        results = []
        for row in rows:
            unread_count = row["unread_count"] or 0
            results.append(SourceMeta(
                id=row["id"],
                url=row["url"],
                title=row["title"],
                category=row["category"],
                unread_count=unread_count,
                has_unread=unread_count > 0,
                latest_entry_at=row["latest_entry_at"],
            ))
        return results


@app.post("/sources", response_model=SourceResponse)
def create_source(payload: SourceCreate):
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO sources (url, title, category) VALUES (?, ?, ?)",
            (payload.url, payload.title, payload.category),
        )
        if cursor.lastrowid:
            source_id = cursor.lastrowid
        else:
            # URL 已存在，查询 ID
            source_id = conn.execute(
                "SELECT id FROM sources WHERE url = ?", (payload.url,)
            ).fetchone()["id"]

        row = conn.execute(
            "SELECT id, url, title, category FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return dict(row)


@app.delete("/sources/{source_id}")
def delete_source(source_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    return {"status": "deleted"}


# 供其他服务调用的内部 API
@app.get("/sources/{source_id}")
def get_source(source_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, url, title, category FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Source not found")
        return dict(row)


# gRPC 端口
GRPC_PORT = 50051
