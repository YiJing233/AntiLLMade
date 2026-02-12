from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
from dateutil import parser as date_parser
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from storage import (
    Entry,
    add_entries,
    add_source,
    delete_source,
    get_source_map,
    init_db,
    list_entries_by_date,
    list_sources,
    list_sources_with_meta,
    mark_entry_read,
)
from summarizer import summarize_text

app = FastAPI(title="AI RSS Digest")


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


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


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
def ingest_feeds() -> Dict[str, Any]:
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
            summary = summarize_text(content)
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
