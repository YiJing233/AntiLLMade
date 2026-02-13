# API Gateway - 统一的 API 网关
# 路由、限流、认证、熔断

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import os
import httpx
import time
from ratelimit import RateLimitMiddleware, Rule
from redis.asyncio import Redis

# 配置
PORT = int(os.getenv("GATEWAY_PORT", "8000"))
SERVICES = {
    "frontend": os.getenv("FRONTEND_URL", "http://localhost:5173"),
    "source": os.getenv("SOURCE_SERVICE_URL", "http://localhost:8002"),
    "rss": os.getenv("RSS_SERVICE_URL", "http://localhost:8003"),
    "summary": os.getenv("SUMMARY_SERVICE_URL", "http://localhost:8001"),
    "digest": os.getenv("DIGEST_SERVICE_URL", "http://localhost:8004"),
    "data": os.getenv("DATA_SERVICE_URL", "http://localhost:8005"),
}

redis: Optional[Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis
    redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    print(f"API Gateway started on port {PORT}")
    yield
    await redis.close()


app = FastAPI(
    title="AntiLLMade API Gateway",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 限流 (简单版本)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    key = f"ratelimit:{client_ip}"
    
    # 简单限流: 每分钟 100 次
    count = await redis.incr(key)
    await redis.expire(key, 60)
    
    if count > 100:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests"}
        )
    
    response = await call_next(request)
    return response


class GatewayResponse(BaseModel):
    status: str
    services: Dict[str, str]
    version: str = "1.0.0"


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/", response_model=GatewayResponse)
def root():
    return GatewayResponse(
        status="ok",
        services={name: url for name, url in SERVICES.items()},
    )


# ========== 路由转发 ==========

async def proxy_request(service: str, path: str, method: str, body: Optional[dict] = None):
    """转发请求到下游服务"""
    base_url = SERVICES.get(service)
    if not base_url:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    
    url = f"{base_url}/{path}"
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, params=body)
            elif method == "POST":
                response = await client.post(url, json=body)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                raise HTTPException(status_code=400, detail="Unsupported method")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


# Source Service 路由
@app.get("/sources")
async def list_sources():
    return await proxy_request("source", "sources", "GET")


@app.get("/sources/meta")
async def sources_meta():
    return await proxy_request("source", "sources/meta", "GET")


@app.post("/sources")
async def create_source(body: dict):
    return await proxy_request("source", "sources", "POST", body)


@app.delete("/sources/{source_id}")
async def delete_source(source_id: int):
    return await proxy_request("source", f"sources/{source_id}", "DELETE")


# RSS Service 路由
@app.post("/ingest")
async def start_ingest(body: Optional[dict] = None):
    return await proxy_request("rss", "ingest", "POST", body or {})


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    return await proxy_request("rss", f"job/{job_id}", "GET")


# Digest Service 路由
@app.get("/digest")
async def get_digest(date: Optional[str] = None):
    return await proxy_request("digest", f"digest?date={date or ''}", "GET")


@app.post("/digest/{date}/regenerate")
async def regenerate_digest(date: str):
    return await proxy_request("digest", f"digest/{date}/regenerate", "POST")


# Entry 路由
@app.post("/entries/{entry_id}/read")
async def mark_entry_read(entry_id: int):
    return await proxy_request("data", f"entries/{entry_id}/read", "POST")


# Summary Service 路由
@app.post("/summarize")
async def summarize(body: dict):
    return await proxy_request("summary", "summarize", "POST", body)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
