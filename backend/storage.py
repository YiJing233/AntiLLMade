import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

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
        conn.executescript(
            """
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
            """
        )
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
            results.append(
                {
                    "id": row["id"],
                    "url": row["url"],
                    "title": row["title"],
                    "category": row["category"],
                    "unread_count": unread_count,
                    "has_unread": unread_count > 0,
                    "latest_entry_at": row["latest_entry_at"],
                }
            )
        return results


def get_source_map() -> dict[int, Source]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, url, title, category FROM sources"
        ).fetchall()
        return {row["id"]: Source(**row) for row in rows}
