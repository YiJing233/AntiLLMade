-- Data Service 数据库初始化脚本
-- PostgreSQL Schema

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sources 表
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '默认',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sources_category ON sources(category);

-- Entries 表
CREATE TABLE IF NOT EXISTS entries (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    unread BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, link)
);

CREATE INDEX IF NOT EXISTS idx_entries_published_at ON entries(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_entries_source_id ON entries(source_id);
CREATE INDEX IF NOT EXISTS idx_entries_unread ON entries(unread) WHERE unread = TRUE;

-- Digests 表 (可选：存储生成的日报)
CREATE TABLE IF NOT EXISTS digests (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    content JSONB NOT NULL,
    category_count INTEGER NOT NULL DEFAULT 0,
    total_entries INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_digests_date ON digests(date DESC);

-- 触发器: 更新时间
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_sources_updated_at ON sources;
CREATE TRIGGER update_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
