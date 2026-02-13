# RSS Service - 事件驱动架构
# 独立的 RSS 聚合微服务，支持异步事件发布

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import feedparser
import httpx
import json
from datetime import datetime
from typing import List, Optional
import os
import redis.asyncio as redis

# 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
STREAMS_KEY = "antiLLMade:events"
SUMMARY_SERVICE_URL = os.getenv("SUMMARY_SERVICE_URL", "http://localhost:8001")
MAX_CONCURRENT = 5  # 并发拉取数量

redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    print(f"RSS Service started, REDIS_URL={REDIS_URL}")
    yield
    await redis_client.close()


app = FastAPI(title="RSS Aggregator Service", lifespan=lifespan)


class FeedInfo(BaseModel):
    url: str
    title: str
    entry_count: int


class IngestResponse(BaseModel):
    job_id: str
    status: str
    source_count: int


class SourceCreate(BaseModel):
    url: str
    title: str
    category: str = "默认"


async def publish_event(event_type: str, data: dict):
    """发布事件到 Redis Streams"""
    if redis_client:
        event = {
            "type": event_type,
            "data": json.dumps(data, default=str),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await redis_client.xadd(STREAMS_KEY, event)


async def fetch_and_summarize(url: str, source_id: int, source_title: str, category: str) -> List[dict]:
    """拉取 RSS 并异步调用摘要服务"""
    entries = []
    try:
        feed = feedparser.parse(url)
        for item in feed.entries[:20]:  # 限制每个源最多20条
            content = item.get("summary") or item.get("description") or ""
            
            # 调用摘要服务
            summary = await summarize_content(content)
            
            entry = {
                "source_id": source_id,
                "title": item.get("title", "无标题"),
                "link": item.get("link", ""),
                "content": content,
                "summary": summary,
                "published_at": datetime.utcnow().isoformat(),
                "category": category,
                "source_title": source_title,
            }
            entries.append(entry)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    
    return entries


async def summarize_content(content: str) -> str:
    """调用 Summary Service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SUMMARY_SERVICE_URL}/summarize",
                json={"text": content, "use_cache": True},
            )
            response.raise_for_status()
            return response.json()["summary"]
    except Exception as e:
        print(f"Summary service error: {e}")
        from textwrap import shorten
        return shorten(content, width=240, placeholder="...")


@app.get("/health")
def health():
    return {"status": "ok", "service": "rss"}


@app.post("/ingest", response_model=IngestResponse)
async def start_ingest(sources: Optional[List[SourceCreate]] = None):
    """
    触发 RSS 拉取 - 异步模式
    立即返回 job_id，实际处理在后台进行
    """
    import uuid
    
    job_id = str(uuid.uuid4())[:8]
    
    # 发布 ingest 事件
    await publish_event("ingest.started", {
        "job_id": job_id,
        "source_count": len(sources) if sources else 0,
    })
    
    # 后台任务
    asyncio.create_task(process_ingest(job_id, sources))
    
    return IngestResponse(
        job_id=job_id,
        status="processing",
        source_count=len(sources) if sources else 0
    )


async def process_ingest(job_id: str, sources: Optional[List[SourceCreate]]):
    """后台处理 ingest"""
    try:
        # 获取订阅源列表
        if sources:
            source_list = [(s.url, s.title, s.category) for s in sources]
        else:
            # 从 Source Service 获取
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:8002/sources")
                sources_data = resp.json()
                source_list = [(s["url"], s["title"], s["category"]) for s in sources_data]
        
        total_entries = 0
        
        # 并发拉取 (限制并发数)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def fetch_with_limit(url, title, category):
            async with semaphore:
                return await fetch_and_summarize(url, 0, title, category)
        
        tasks = [fetch_with_limit(url, title, category) for url, title, category in source_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_entries = []
        for result in results:
            if isinstance(result, list):
                all_entries.extend(result)
        
        total_entries = len(all_entries)
        
        # 发布完成事件
        await publish_event("ingest.completed", {
            "job_id": job_id,
            "total_entries": total_entries,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        print(f"Job {job_id} completed: {total_entries} entries")
        
    except Exception as e:
        await publish_event("ingest.failed", {
            "job_id": job_id,
            "error": str(e),
        })
        print(f"Job {job_id} failed: {e}")


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """查询任务状态"""
    if redis_client:
        # 从 Streams 获取事件
        events = await redis_client.xrange(f"{STREAMS_KEY}:{job_id}", count=1)
        if events:
            return {"job_id": job_id, "status": "completed"}
    
    return {"job_id": job_id, "status": "processing"}
