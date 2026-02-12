import os
from textwrap import shorten
from typing import Optional

import httpx


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def summarize_text(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "暂无可用内容。"
    if OPENAI_API_KEY:
        summary = _summarize_with_openai(cleaned)
        if summary:
            return summary
    return shorten(cleaned, width=240, placeholder="...")


def _summarize_with_openai(text: str) -> Optional[str]:
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
                    "content": (
                        "你是新闻摘要助手。请给出一句话总结，并列出2-3条关键信息。"
                    ),
                },
                {"role": "user", "content": text[:6000]},
            ],
            "temperature": 0.3,
        }
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
