# Digest Service - 日报聚合服务
# 独立的日报聚合微服务

from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
STREAMS_KEY = "antiLLMade:events"

redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    print(f"Digest Service started, REDIS_URL={REDIS_URL}")
    yield
    await redis_client.close()


app = FastAPI(title="Digest Aggregation Service", lifespan=lifespan)


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


class EntryInput(BaseModel):
    id: int
    source_id: int
    title: str
    link: str
    content: str
    summary: str
    published_at: str
    category: str
    source_title: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "digest"}


@app.get("/digest", response_model=DailyDigest)
def get_digest(date: Optional[str] = None) -> DailyDigest:
    """获取日报"""
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    
    # 从 Redis 获取当日条目
    entries = _get_entries_from_cache(target_date)
    
    # 按分类分组
    categories: Dict[str, List[DigestEntry]] = {}
    for entry in entries:
        digest_entry = DigestEntry(**entry)
        categories.setdefault(digest_entry.category, []).append(digest_entry)
    
    return DailyDigest(
        date=target_date,
        total=len(entries),
        categories=categories,
    )


def _get_entries_from_cache(date: str) -> List[dict]:
    """从缓存获取当日条目"""
    if redis_client:
        key = f"digest:{date}"
        data = redis_client.lrange(key, 0, -1)
        if data:
            return [json.loads(item) for item in data]
    return []


@app.post("/digest/{date}/regenerate")
def regenerate_digest(date: str):
    """重新生成日报"""
    # 触发事件
    if redis_client:
        import uuid
        job_id = str(uuid.uuid4())[:8]
        redis_client.xadd(STREAMS_KEY, {
            "type": "digest.regenerate",
            "data": json.dumps({"date": date, "job_id": job_id}),
        })
        return {"job_id": job_id, "status": "regenerating"}
    return {"status": "error", "message": "Redis not available"}


# 事件处理 (订阅模式)
async def subscribe_events():
    """订阅事件流"""
    if redis_client:
        async for message in redis_client.xread({STREAMS_KEY: "0"}):
            stream, messages = message
            for msg in messages:
                event_type = msg[b"type"].decode()
                if event_type == "entry.summarized":
                    # 新条目摘要完成，添加到日报
                    data = json.loads(msg[b"data"])
                    _add_to_digest(data)


def _add_to_digest(entry_data: dict):
    """添加条目到日报"""
    if redis_client:
        date = entry_data.get("published_at", "")[:10]
        key = f"digest:{date}"
        redis_client.lpush(key, json.dumps(entry_data))
        # 设置过期时间 7 天
        redis_client.expire(key, 604800)
