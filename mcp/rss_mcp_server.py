import json
import os
from datetime import datetime
from typing import Any, Dict

import httpx

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "缺少 mcp 依赖，请先在虚拟环境中 pip install mcp"
    ) from exc

API_BASE = os.getenv("RSS_API_BASE", "http://localhost:8000")

mcp = FastMCP("rss-digest")


def _request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
    response = httpx.request(
        method,
        f"{API_BASE}{path}",
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
async def list_sources() -> str:
    """列出当前订阅源。"""
    sources = _request("GET", "/sources")
    return json.dumps(sources, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_sources_meta() -> str:
    """列出订阅源元信息（未读数、最新更新时间）。"""
    sources = _request("GET", "/sources/meta")
    return json.dumps(sources, ensure_ascii=False, indent=2)


@mcp.tool()
async def add_source(url: str, title: str, category: str = "默认") -> str:
    """添加一个 RSS 订阅源。"""
    source = _request("POST", "/sources", {"url": url, "title": title, "category": category})
    return json.dumps(source, ensure_ascii=False, indent=2)


@mcp.tool()
async def ingest_now() -> str:
    """立即拉取全部订阅源的最新内容。"""
    result = _request("POST", "/ingest")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def mark_entry_read(entry_id: int) -> str:
    """将指定条目标记为已读。"""
    result = _request("POST", f"/entries/{entry_id}/read")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_daily_digest(date: str | None = None) -> str:
    """获取指定日期的日报，默认今日。"""
    target = date or datetime.utcnow().strftime("%Y-%m-%d")
    digest = _request("GET", f"/digest?date={target}")
    return json.dumps(digest, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
