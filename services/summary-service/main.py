# AI Summary Service
# 独立的 AI 摘要生成微服务

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os
from contextlib import asynccontextmanager

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# 简单的内存缓存 (生产环境用 Redis)
_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接 Redis (可选)
    print(f"Summary Service started, REDIS_URL={REDIS_URL}")
    yield
    # 清理

app = FastAPI(title="AI Summary Service", lifespan=lifespan)


class SummarizeRequest(BaseModel):
    text: str
    use_cache: bool = True


class SummarizeResponse(BaseModel):
    summary: str
    cached: bool = False
    model: str = OPENAI_MODEL


@app.get("/health")
def health():
    return {"status": "ok", "service": "summary"}


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    # 缓存检查
    if request.use_cache:
        cache_key = request.text[:100]  # 简化缓存键
        if cache_key in _cache:
            return SummarizeResponse(summary=_cache[cache_key], cached=True)

    # 清理文本
    cleaned = " ".join(request.text.split())
    if not cleaned:
        return SummarizeResponse(summary="暂无可用内容。")

    # OpenAI 摘要
    if OPENAI_API_KEY:
        summary = await _summarize_with_openai(cleaned)
        if summary:
            _cache[cache_key] = summary
            return SummarizeResponse(summary=summary)

    # 回退: 文本截取
    from textwrap import shorten
    summary = shorten(cleaned, width=240, placeholder="...")
    return SummarizeResponse(summary=summary)


async def _summarize_with_openai(text: str) -> str | None:
    """调用 OpenAI API 生成摘要"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是新闻摘要助手。请给出一句话总结，并列出2-3条关键信息。",
                },
                {"role": "user", "content": text[:6000]},
            ],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None


# gRPC 端口 (可选)
GRPC_PORT = 50052
