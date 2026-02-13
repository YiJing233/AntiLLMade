# MCP Tool Service - 独立的 MCP 工具服务
# 为 Codex/Agent 提供工具接口

from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import httpx
import os

# 配置
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

app = FastAPI(title="MCP Tool Service")


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("MCP Tool Service started")
    yield


# ========== RSS/Digest 工具 ==========

async def list_sources() -> List[Dict]:
    """列出所有订阅源"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/sources")
        resp.raise_for_status()
        return resp.json()


async def add_source(url: str, title: str, category: str = "默认") -> Dict:
    """添加订阅源"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/sources",
            json={"url": url, "title": title, "category": category}
        )
        resp.raise_for_status()
        return resp.json()


async def get_digest(date: Optional[str] = None) -> Dict:
    """获取日报"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/digest?date={date or ''}")
        resp.raise_for_status()
        return resp.json()


async def trigger_ingest(sources: Optional[List[Dict]] = None) -> Dict:
    """触发 RSS 拉取"""
    async with httpx.AsyncClient(timeout=300) as client:
        body = {"sources": sources} if sources else {}
        resp = await client.post(f"{GATEWAY_URL}/ingest", json=body)
        resp.raise_for_status()
        return resp.json()


async def mark_entry_read(entry_id: int) -> Dict:
    """标记条目已读"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{GATEWAY_URL}/entries/{entry_id}/read")
        resp.raise_for_status()
        return resp.json()


# ========== MCP 工具注册 ==========

TOOLS = [
    {
        "name": "list_sources",
        "description": "列出所有 RSS 订阅源",
        "parameters": {},
    },
    {
        "name": "add_source",
        "description": "添加新的 RSS 订阅源",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "RSS 订阅源 URL"},
                "title": {"type": "string", "description": "订阅源名称"},
                "category": {"type": "string", "description": "分类标签"},
            },
            "required": ["url", "title"],
        },
    },
    {
        "name": "get_daily_digest",
        "description": "获取每日 RSS 摘要日报",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "日期 (YYYY-MM-DD)，默认今天"},
            },
        },
    },
    {
        "name": "trigger_ingest",
        "description": "触发 RSS 内容拉取和摘要生成",
        "parameters": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "description": "指定拉取的订阅源列表，默认全部",
                },
            },
        },
    },
    {
        "name": "mark_entry_read",
        "description": "标记特定条目为已读",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "条目 ID"},
            },
            "required": ["entry_id"],
        },
    },
]


# ========== API 端点 ==========

@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp"}


@app.get("/tools")
def list_tools():
    """列出可用工具"""
    return {"tools": TOOLS}


@app.post("/tools/call")
async def call_tool(call: ToolCall) -> ToolResult:
    """调用工具"""
    try:
        if call.name == "list_sources":
            result = await list_sources()
        elif call.name == "add_source":
            result = await add_source(**call.arguments)
        elif call.name == "get_daily_digest":
            result = await get_digest(call.arguments.get("date"))
        elif call.name == "trigger_ingest":
            result = await trigger_ingest(call.arguments.get("sources"))
        elif call.name == "mark_entry_read":
            result = await mark_entry_read(**call.arguments)
        else:
            return ToolResult(success=False, error=f"Unknown tool: {call.name}")
        
        return ToolResult(success=True, result=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
