#!/usr/bin/env python3
"""
RSS 文摘编辑器 Agent

自动抓取 RSS 更新，生成精选摘要。
"""

import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json


RSS_API_BASE = "http://localhost:8000"


def ingest_feeds() -> Dict[str, Any]:
    """抓取最新 RSS 内容"""
    r = httpx.post(f"{RSS_API_BASE}/ingest")
    return r.json()


def get_sources_with_unread() -> List[Dict[str, Any]]:
    """获取有未读内容的订阅源"""
    r = httpx.get(f"{RSS_API_BASE}/sources/meta")
    return [s for s in r.json() if s.get('unread_count', 0) > 0]


def get_digest(date: str = None) -> Dict[str, Any]:
    """获取指定日期的日报"""
    date = date or datetime.utcnow().strftime("%Y-%m-%d")
    r = httpx.get(f"{RSS_API_BASE}/digest", params={"date": date})
    return r.json()


def generate_summary(entries: List[Dict], max_entries: int = 10) -> List[Dict[str, str]]:
    """生成精选摘要"""
    summaries = []
    
    for i, entry in enumerate(entries[:max_entries]):
        summary = {
            "index": i + 1,
            "title": entry.get("title", "无标题"),
            "source": entry.get("source_title", "未知来源"),
            "summary": clean_summary(entry.get("summary", "")),
            "link": entry.get("link", "")
        }
        summaries.append(summary)
    
    return summaries


def clean_summary(text: str, max_words: int = 100) -> str:
    """清理和截取摘要"""
    # 移除 HTML 标签
    import re
    text = re.sub(r'<[^>]+>', '', text)
    # 解码 HTML 实体
    text = text.replace('&#8217;', "'").replace('&#8230;', '...')
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    # 截取指定词数
    words = text.split()[:max_words]
    return ' '.join(words) + ('...' if len(text.split()) > max_words else '')


def format_digest_report(summary_data: Dict) -> str:
    """格式化日报报告"""
    entries = summary_data.get('entries', [])
    categories = summary_data.get('categories', {})
    
    if not entries:
        return "📭 今日暂无新内容更新"
    
    report = f"## 📰 RSS 文摘日报 - {datetime.now().strftime('%Y年%m月%d日')}\n\n"
    report += f"**来源**: {len(entries)} 个订阅源\n\n"
    report += "---\n\n"
    
    # 按分类展示
    for category, cat_entries in categories.items():
        report += f"### 📁 {category}\n\n"
        for entry in cat_entries[:5]:  # 每类最多5条
            report += f"**{entry['title'][:60]}...**\n\n"
            report += f"> {clean_summary(entry.get('summary', ''), 50)}\n\n"
        report += "\n"
    
    # 精选摘要
    report += "### ✨ 精选摘要\n\n"
    selected = generate_summary(entries, 8)
    for item in selected:
        report += f"**{item['index']}. {item['title'][:50]}...**\n\n"
        report += f"> 来源: {item['source']}\n\n"
        report += f">{item['summary']}\n\n"
    
    report += f"\n💡 共收录 {len(entries)} 条更新，来源: {', '.join(set(e.get('source_title', '') for e in entries))}"
    
    return report


def run():
    """执行文摘生成流程"""
    print("📥 开始抓取 RSS 更新...")
    
    # 1. 抓取新内容
    ingest_result = ingest_feeds()
    print(f"✅ 抓取完成: 新增 {ingest_result.get('inserted', 0)} 条")
    
    # 2. 获取未读源
    unread_sources = get_sources_with_unread()
    print(f"📚 有更新的订阅源: {len(unread_sources)}")
    
    # 3. 获取日报数据
    today = datetime.utcnow().strftime("%Y-%m-%d")
    digest = get_digest(today)
    
    # 4. 生成报告
    report = format_digest_report(digest)
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    return report


if __name__ == "__main__":
    run()
