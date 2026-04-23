"""FastAPI server for Telegram Bot Webhook."""

import os
import asyncio
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import pydantic

from .config.settings import (
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_ID, 
    GROQ_API_KEY, 
    HF_TOKEN, 
    HF_MODEL,
    USE_HF,
    ensure_data_dir
)
from .schemas.models import (
    JobListing,
    SearchResult,
    filter_recent_jobs,
    sort_by_recent,
    filter_by_experience
)
from .agents.query_parser import parse
from .tools.scraper import JobScraper


app = FastAPI(title="AI Job Finder API", version="1.0.0")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8723909515:AAGn_5Da8T6z7QULdpQRbZ30vvVGlcmnxAc")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5366460033")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")


def create_error_response(message: str) -> JSONResponse:
    """Create error response."""
    return JSONResponse({"error": message}, status_code=500)


def create_success_response(data: dict) -> JSONResponse:
    """Create success response."""
    return JSONResponse(data)


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    """Send message via Telegram API."""
    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            return response.status_code == 200
    except Exception:
        return False


def format_job_message(jobs: list, max_count: int = 5, show_time: bool = True) -> str:
    """Format jobs for Telegram response."""
    if not jobs:
        return "No recent jobs found. Try a different search."

    header = f"Latest Jobs ({len(jobs)} found)\n\n"
    message = header

    for i, job in enumerate(jobs[:max_count], 1):
        message += f"{i}. {job.title}\n"
        message += f"   {job.company}\n"

        if job.location:
            message += f"   {job.location}\n"

        if show_time and job.posted_time:
            message += f"   {job.posted_time}\n"

        if job.salary:
            message += f"   {job.salary}\n"

        if job.url:
            message += f"   Apply: {job.url}\n"

        message += "\n---\n\n"

    remaining = len(jobs) - max_count
    if remaining > 0:
        message += f"Plus {remaining} more jobs...\n"

    message += "\nKeep applying!"
    return message


async def process_job_search(prompt: str, max_results: int = 10) -> tuple[list, dict]:
    """Process job search request."""
    print(f"\nProcessing: {prompt}")

    query = parse(prompt)
    print(f"Query: {query.model_dump_json()}")

    async with JobScraper() as scraper:
        jobs = await scraper.scrape(query, max_results)

    print(f"Found {len(jobs)} jobs")

    recent_jobs = filter_recent_jobs(jobs, max_hours=24)
    print(f"Recent (24h): {len(recent_jobs)} jobs")

    exp_jobs = filter_by_experience(recent_jobs, level="fresher")
    print(f"Fresher: {len(exp_jobs)} jobs")

    sorted_jobs = sort_by_recent(exp_jobs or recent_jobs)

    query_info = {
        "keywords": query.keywords,
        "location": query.location,
        "remote": query.remote,
        "experience": query.experience
    }

    return sorted_jobs[:max_results], query_info


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "AI Job Finder API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_configured": bool(BOT_TOKEN),
        "groq_configured": bool(GROQ_KEY),
        "hf_configured": bool(USE_HF),
        "model": HF_MODEL if USE_HF else "groq"
    }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook handler."""
    try:
        data = await request.json()
    except Exception:
        return create_error_response("Invalid request")

    if "message" not in data:
        return create_success_response({"ok": True})

    message = data["message"]
    text = message.get("text", "")
    chat_id = str(message["chat"]["id"])

    if not text:
        return create_success_response({"ok": True})

    print(f"\n💬 Received: {text}")

    commands = ["/start", "/help", "/search", "/jobs", "/alerts", "/stop"]
    is_command = any(text.strip().startswith(cmd) for cmd in commands)

    if text.startswith("/start"):
        welcome = (
            "Welcome to AI Job Finder!\n\n"
            "I'll help you find your dream job.\n\n"
            "How to use:\n"
            "- Send a job search like 'Python developer remote'\n"
            "- Add 'fresher' for entry-level jobs\n"
            "- Add location like 'in Bangalore'\n\n"
            "Try: Python fresher remote in India"
        )
        await send_telegram_message(chat_id, welcome)
        return create_success_response({"ok": True})

    if text.startswith("/help"):
        help_text = (
            "Help\n\n"
            "Search examples:\n"
            "- Python developer remote\n"
            "- AI fresher in India\n"
            "- React WFH\n\n"
            "Tips:\n"
            "- Add 'remote' for work from home\n"
            "- Add 'fresher' for entry-level\n"
            "- Add city for local jobs"
        )
        await send_telegram_message(chat_id, help_text)
        return create_success_response({"ok": True})

    if text.startswith("/search "):
        prompt = text.replace("/search ", "").strip()
    else:
        prompt = text

    jobs, query_info = await process_job_search(prompt, max_results=5)
    response = format_job_message(jobs, show_time=True)

    await send_telegram_message(chat_id, response)
    return create_success_response({"ok": True, "jobs_found": len(jobs)})


@app.post("/search")
async def api_search(request: Request):
    """API endpoint for job search."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    max_results = body.get("max_results", 10)
    experience = body.get("experience", "fresher")
    max_hours = body.get("max_hours", 24)

    jobs, query_info = await process_job_search(prompt, max_results)

    results = []
    for job in jobs:
        results.append({
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "posted_time": job.posted_time,
            "salary": job.salary,
            "source": job.source
        })

    return {
        "query": query_info,
        "jobs": results,
        "total_found": len(jobs)
    }


@app.post("/send-alert")
async def send_alert(request: Request):
    """Manual alert trigger."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")

    prompt = body.get("prompt", "python developer remote fresher")
    chat_id = body.get("chat_id", CHAT_ID)

    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")

    jobs, _ = await process_job_search(prompt, max_results=5)
    message = format_job_message(jobs)

    success = await send_telegram_message(chat_id, message)

    return {"ok": success, "jobs_sent": len(jobs)}


@app.on_event("startup")
async def startup_event():
    """Run on startup."""
    ensure_data_dir()
    llm_info = "DeepSeek-R1 via HuggingFace" if USE_HF else "Groq LLaMA"
    print(f"AI Job Finder API started (LLM: {llm_info})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)