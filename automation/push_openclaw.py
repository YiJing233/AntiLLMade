import json
import os
from datetime import datetime

import httpx

API_BASE = os.getenv("RSS_API_BASE", "http://localhost:8000")
OPENCLAW_WEBHOOK = os.getenv("OPENCLAW_WEBHOOK")


def main() -> None:
    if not OPENCLAW_WEBHOOK:
        raise SystemExit("请设置 OPENCLAW_WEBHOOK 环境变量")
    target_date = datetime.utcnow().strftime("%Y-%m-%d")
    digest = httpx.get(f"{API_BASE}/digest?date={target_date}", timeout=20).json()
    payload = {
        "type": "rss-daily-digest",
        "date": digest.get("date"),
        "total": digest.get("total"),
        "categories": digest.get("categories"),
    }
    response = httpx.post(OPENCLAW_WEBHOOK, json=payload, timeout=20)
    response.raise_for_status()
    print(json.dumps({"status": "sent", "response": response.text}, ensure_ascii=False))


if __name__ == "__main__":
    main()
