# AGENTS.md - Developer Instructions

## Run Commands

```bash
# Server (FastAPI on port 8000)
python -m src.server

# Or with uvicorn
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000

# Telegram bot (polling)
python -m src.bot

# CLI search
python -m src.main "python developer fresher India"
```

## Critical Setup

- **Python version**: 3.12 (not 3.14 - dependencies don't support it)
- **Install Playwright**: `playwright install chromium`
- **Environment**: Copy `.env.example` to `.env` and fill values

## Architecture

| Entry | File | Description |
|-------|------|-------------|
| FastAPI server | `src/server.py` | Web API + webhook |
| Telegram bot | `src/bot.py` | Bot handlers |
| Job pipeline | `src/job_search.py` | Main search logic |
| CLI | `src/main.py` | Command-line |

## Key Directories

- `src/agents/` - AI agents (query_parser, ranker, resume_matcher, job_filter)
- `src/tools/scrapers/` - Job scrapers (indeed.py, naukri.py, linkedin.py, google_jobs.py, dispatcher.py)
- `src/services/` - Storage, memory, Telegram
- `src/utils/` - Time utilities (extract_hours, is_recent_job)

## Important Files

- `.env` - Environment variables (not tracked in git)
- `data/` - JSON storage (jobs.json, user_prefs.json, user_context.json)
- `runtime.txt` - Must contain `python_version = "3.12"`

## Testing

```python
# Quick test import
python -c "from src.job_search import run_prompt_search; print('OK')"
```

## Common Issues

1. **Playwright not installed**: Run `pip install playwright && playwright install chromium`
2. **Windows emoji errors**: Use `chcp 65001` before running, or remove emojis from code
3. **Scraper async errors**: Fallback URL scraper in `http_scraper.py` works when Playwright fails
4. **Module import errors**: Use `python -m src.server` not `python src/server.py`

## Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<RENDER_URL>/webhook"
```

## Build on Windows

Avoid `&&` - use separate commands:
```cmd
cd /d C:\Users\ramak\OneDrive\Ram\projects\job
python -m src.server
```