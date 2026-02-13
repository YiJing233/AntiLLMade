# Scheduler Service - 自动化调度服务
# 基于 Cron 的定时任务调度

from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import httpx
import os

# 配置
SCHEDULE_INTERVAL = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "60"))
INGEST_ENDPOINT = os.getenv("INGEST_ENDPOINT", "http://localhost:8000/ingest")
NOTIFICATION_WEBHOOK = os.getenv("NOTIFICATION_WEBHOOK", "")

app = FastAPI(title="Scheduler Service")


class JobStatus(BaseModel):
    job_id: str
    name: str
    schedule: str
    last_run: Optional[str]
    next_run: Optional[str]
    status: str


jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动调度器
    print(f"Scheduler started, interval={SCHEDULE_INTERVAL}min")
    asyncio.create_task(scheduler_loop())
    yield


async def scheduler_loop():
    """主调度循环"""
    while True:
        try:
            # 触发 ingest 任务
            await trigger_ingest()
            jobs["ingest"]["last_run"] = datetime.utcnow().isoformat()
            jobs["ingest"]["next_run"] = (
                datetime.utcnow() + timedelta(minutes=SCHEDULE_INTERVAL)
            ).isoformat()
        except Exception as e:
            jobs["ingest"]["status"] = f"error: {e}"
            print(f"Ingest job error: {e}")
        
        await asyncio.sleep(SCHEDULE_INTERVAL * 60)


async def trigger_ingest():
    """触发 RSS 拉取"""
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(INGEST_ENDPOINT, json={})
        response.raise_for_status()
        
        # 发送通知
        if NOTIFICATION_WEBHOOK:
            await client.post(
                NOTIFICATION_WEBHOOK,
                json={
                    "type": "ingest_completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": response.json(),
                }
            )


# ========== API ==========

@app.on_event("startup")
def startup():
    # 注册任务
    jobs["ingest"] = {
        "job_id": "ingest",
        "name": "RSS Ingest",
        "schedule": f"每 {SCHEDULE_INTERVAL} 分钟",
        "last_run": None,
        "next_run": None,
        "status": "scheduled",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduler"}


@app.get("/jobs", response_model=list[JobStatus])
def list_jobs():
    return [JobStatus(**job) for job in jobs.values()]


@app.post("/jobs/{job_id}/run")
async_id: str):
 def run_job(job    """手动触发任务"""
    if job_id == "ingest":
        asyncio.create_task(trigger_ingest())
        return {"status": "triggered", "job_id": job_id}
    return {"error": "Job not found"}


@app.get("/status")
def status():
    return {
        "service": "scheduler",
        "interval_minutes": SCHEDULE_INTERVAL,
        "active_jobs": len(jobs),
        "timestamp": datetime.utcnow().isoformat(),
    }
