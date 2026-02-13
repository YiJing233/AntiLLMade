# 共享模型定义
# 供所有服务使用的 Pydantic 模型

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Source(BaseModel):
    id: int
    url: str
    title: str
    category: str


class Entry(BaseModel):
    id: int
    source_id: int
    title: str
    link: str
    published_at: datetime
    summary: str
    content: str
    unread: bool


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
    categories: dict[str, List[DigestEntry]]


# 事件模型 (用于消息队列)
class EntryCreatedEvent(BaseModel):
    entry_id: int
    source_id: int
    title: str
    content: str
    published_at: datetime


class EntrySummarizedEvent(BaseModel):
    entry_id: int
    summary: str
    model: str


class DigestReadyEvent(BaseModel):
    date: str
    category_count: int
    total_entries: int


# 异常定义
class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
