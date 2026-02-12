---
name: rss-daily-briefing
description: "Build and operate AI-aware RSS daily digest systems with configurable sources, daily summaries, and optional MCP/Codex/OpenClaw automation integrations. Use when Codex needs to create or update RSS digest apps, MCP tools, automation push pipelines, or daily briefing workflows."
---

# RSS Daily Briefing Skill

## Quick workflow

1. Initialize the backend service and database.
2. Configure RSS sources and category tags.
3. Run ingest and generate the daily digest payloads.
4. Wire up the frontend and automation push channels.
5. (Optional) Expose MCP tools for source management and digest fetch.

## Backend checklist

- Use FastAPI with endpoints:
  - `POST /sources` to add RSS sources
  - `GET /sources` to list sources
  - `POST /ingest` to pull and summarize
  - `GET /digest?date=YYYY-MM-DD` to fetch grouped digest
- Store entries in SQLite with `published_at`, `summary`, and `content`.
- Summarization fallback: if no LLM key, return compact extract (first 240 chars).

## Frontend checklist

- Show a dashboard with:
  - Source list
  - Daily digest grouped by category
  - Summary + detail sections
- Include actions to trigger ingest and refresh.

## MCP server checklist

- Provide tools:
  - `list_sources`
  - `add_source`
  - `ingest_now`
  - `get_daily_digest`
- Allow base URL configuration via env var `RSS_API_BASE`.

## Automation integrations

- Provide a JSON/YAML config with placeholders for:
  - Codex automation schedules
  - OpenClaw webhook/URL
- When integrating, describe expected payload shape:
  - `date`, `total`, `categories` with entries.

## Output quality bar

- Daily digest should include:
  - Date
  - Total item count
  - Category sections
  - Each item summary and original link
