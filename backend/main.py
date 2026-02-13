from datetime import datetime
from typing import Any, Dict, List, Optional
import os
import asyncio

import httpx
import feedparser
from dateutil import parser as date_parser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 配置外部服务地址
SUMMARY_SERVICE_URL = os.getenv("SUMMARY_SERVICE_URL", "http://localhost:8001")
SOURCE_SERVICE_URL = os.getenv("SOURCE_SERVICE_URL", "http://localhost:8002")

app = FastAPI(title="AI RSS Digest")

# CORS 配置 - 允许 Vercel 前端访问
ALLOWED_ORIGINS = [
    "https://anti-llmade-digest.vercel.app",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SourceCreate(BaseModel):
    url: str
    title: str
    category: str = Field(default="默认")


class DigestEntry(BaseModel):
    id: int
    title: str
    link: str
    published_at: str
    source_title: str
    category: str
    summary: str
    content: str
    unread: bool


class DailyDigest(BaseModel):
    date: str
    total: int
    categories: Dict[str, List[DigestEntry]]


# =====================================
# 外部服务调用 (迭代 1)
# =====================================

async def summarize_text(content: str) -> str:
    """调用外部 Summary Service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SUMMARY_SERVICE_URL}/summarize",
                json={"text": content, "use_cache": True},
            )
            response.raise_for_status()
            return response.json()["summary"]
    except Exception as e:
        print(f"Summary service error: {e}, falling back to text truncation")
        from textwrap import shorten
        return shorten(content, width=240, placeholder="...")


async def fetch_sources() -> List[Dict]:
    """调用外部 Source Service 获取订阅源列表"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SOURCE_SERVICE_URL}/sources")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Source service error: {e}")
        return []


# =====================================
# 内部存储层 (保留向后兼容)
# =====================================

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable

# Railway 持久化存储
if os.getenv("RAILWAY_VOLUME_MOUNT_PATH"):
    DB_PATH = os.path.join(os.getenv("RAILWAY_VOLUME_MOUNT_PATH"), "rss_app.db")
else:
    DB_PATH = "./rss_app.db"


@dataclass
class Source:
    id: int
    url: str
    title: str
    category: str


@dataclass
class Entry:
    id: int
    source_id: int
    title: str
    link: str
    published_at: datetime
    summary: str
    content: str
    unread: bool


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                category TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                published_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                unread INTEGER NOT NULL DEFAULT 1,
                UNIQUE(source_id, link),
                FOREIGN KEY(source_id) REFERENCES sources(id)
            );
        """)
        try:
            conn.execute("ALTER TABLE entries ADD COLUMN unread INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass


def add_source(url: str, title: str, category: str) -> Source:
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO sources (url, title, category) VALUES (?, ?, ?)",
            (url, title, category),
        )
        if cursor.lastrowid:
            source_id = cursor.lastrowid
        else:
            source_id = conn.execute(
                "SELECT id FROM sources WHERE url = ?", (url,)
            ).fetchone()["id"]
        row = conn.execute(
            "SELECT id, url, title, category FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return Source(**row)


def list_sources() -> List[Source]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, url, title, category FROM sources ORDER BY id DESC"
        ).fetchall()
        return [Source(**row) for row in rows]


def delete_source(source_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))


def add_entries(entries: Iterable[Entry]) -> int:
    inserted = 0
    with get_conn() as conn:
        for entry in entries:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO entries (
                    source_id, title, link, published_at, summary, content, unread
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.source_id,
                    entry.title,
                    entry.link,
                    entry.published_at.isoformat(),
                    entry.summary,
                    entry.content,
                    1 if entry.unread else 0,
                ),
            )
            if cursor.rowcount:
                inserted += 1
    return inserted


def list_entries_by_date(date_str: str) -> List[Entry]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, source_id, title, link, published_at, summary, content, unread
            FROM entries
            WHERE date(published_at) = date(?)
            ORDER BY published_at DESC
            """,
            (date_str,),
        ).fetchall()
        entries: List[Entry] = []
        for row in rows:
            entries.append(
                Entry(
                    id=row["id"],
                    source_id=row["source_id"],
                    title=row["title"],
                    link=row["link"],
                    published_at=datetime.fromisoformat(row["published_at"]),
                    summary=row["summary"],
                    content=row["content"],
                    unread=bool(row["unread"]),
                )
            )
        return entries


def mark_entry_read(entry_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE entries SET unread = 0 WHERE id = ?", (entry_id,))


def list_sources_with_meta() -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                sources.id,
                sources.url,
                sources.title,
                sources.category,
                SUM(CASE WHEN entries.unread = 1 THEN 1 ELSE 0 END) AS unread_count,
                MAX(entries.published_at) AS latest_entry_at
            FROM sources
            LEFT JOIN entries ON sources.id = entries.source_id
            GROUP BY sources.id
            ORDER BY sources.id DESC
            """
        ).fetchall()
        results = []
        for row in rows:
            unread_count = row["unread_count"] or 0
            results.append({
                "id": row["id"],
                "url": row["url"],
                "title": row["title"],
                "category": row["category"],
                "unread_count": unread_count,
                "has_unread": unread_count > 0,
                "latest_entry_at": row["latest_entry_at"],
            })
        return results


def get_source_map() -> dict[int, Source]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, url, title, category FROM sources"
        ).fetchall()
        return {row["id"]: Source(**row) for row in rows}


# =====================================
# API 端点
# =====================================

@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "status": "ok",
        "message": "AntiLLMade RSS API (Monolithic)",
        "docs": "/docs",
        "version": "0.2.0",
        "services": {
            "summary": SUMMARY_SERVICE_URL,
            "source": SOURCE_SERVICE_URL,
        },
    }


@app.get("/sources")
def sources() -> List[Dict[str, Any]]:
    return [source.__dict__ for source in list_sources()]


@app.get("/sources/meta")
def sources_meta() -> List[Dict[str, Any]]:
    return list_sources_with_meta()


@app.post("/sources")
def create_source(payload: SourceCreate) -> Dict[str, Any]:
    source = add_source(payload.url, payload.title, payload.category)
    return source.__dict__


@app.delete("/sources/{source_id}")
def remove_source(source_id: int) -> Dict[str, str]:
    delete_source(source_id)
    return {"status": "deleted"}


@app.post("/entries/{entry_id}/read")
def mark_read(entry_id: int) -> Dict[str, str]:
    mark_entry_read(entry_id)
    return {"status": "read"}


@app.post("/ingest")
async def ingest_feeds() -> Dict[str, Any]:
    """拉取 RSS 并生成摘要 - 调用外部 Summary Service"""
    sources = list_sources()
    if not sources:
        raise HTTPException(status_code=400, detail="请先添加 RSS 订阅源。")

    inserted_total = 0
    for source in sources:
        feed = feedparser.parse(source.url)
        new_entries: List[Entry] = []
        for item in feed.entries:
            published = item.get("published") or item.get("updated")
            if published:
                published_at = date_parser.parse(published)
            else:
                published_at = datetime.utcnow()
            content = item.get("summary") or item.get("description") or ""
            summary = await summarize_text(content)  # 调用外部服务
            new_entries.append(
                Entry(
                    id=0,
                    source_id=source.id,
                    title=item.get("title", "无标题"),
                    link=item.get("link", ""),
                    published_at=published_at,
                    summary=summary,
                    content=content,
                    unread=True,
                )
            )
        inserted_total += add_entries(new_entries)

    return {"inserted": inserted_total}


@app.get("/digest", response_model=DailyDigest)
def daily_digest(date: Optional[str] = None) -> DailyDigest:
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    entries = list_entries_by_date(target_date)
    sources = get_source_map()
    categories: Dict[str, List[DigestEntry]] = {}
    for entry in entries:
        source = sources.get(entry.source_id)
        if not source:
            continue
        digest_entry = DigestEntry(
            id=entry.id,
            title=entry.title,
            link=entry.link,
            published_at=entry.published_at.isoformat(),
            source_title=source.title,
            category=source.category,
            summary=entry.summary,
            content=entry.content,
            unread=entry.unread,
        )
        categories.setdefault(source.category, []).append(digest_entry)
    return DailyDigest(date=target_date, total=len(entries), categories=categories)
