"""Notifier Agent - formats and sends Telegram notifications."""

import os
from typing import List, Optional
from telegram import Bot
from telegram.error import TelegramError

from ..schemas.models import MatchResult, JobListing
from ..config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def create_notifier_agent():
    """Create Notifier Agent."""
    from crewai import Agent, LLM
    from ..config.settings import get_llm_config

    llm_config = get_llm_config()
    api_key = os.getenv("GROQ_API_KEY", "")

    return Agent(
        role="Notifier Agent",
        goal="Format job results with personalized messages",
        backstory=(
            "You are a communication expert. You craft personalized job notifications "
            "that are engaging, clear, and motivational. You adapt your tone based "
            "on the user's experience level and make opportunities sound exciting."
        ),
        llm=LLM(
            model=llm_config["model"],
            api_key=api_key,
            temperature=0.7,
            max_tokens=1024
        ),
        verbose=False
    )


NOTIFIER_SYSTEM_PROMPT = """You are a job search notification specialist. 
Create personalized, engaging notifications for job seekers.

Guidelines:
- Keep it conversational and encouraging
- Highlight why each job is a good match
- Include actionable next steps
- Use emojis appropriately but not excessively
- Match the user's experience level (fresher vs senior)
- End with motivation for the search

Input format:
- Job title and company
- Match score
- Skills matched
- Location

Create a concise notification (max 200 words)."""


def format_jobs_message(
    matches: List[MatchResult],
    max_jobs: int = 5,
    custom_prompt: str = None
) -> str:
    """Format matched jobs as Telegram message."""
    if not matches:
        return "No matching jobs found for your profile. Try expanding your skills or adjusting your search criteria."

    message = "🎯 *Your Personalized Job Matches*\n\n"

    for i, match in enumerate(matches[:max_jobs], 1):
        job = match.job
        message += f"*{i}. {job.title}* at {job.company}\n"
        message += f"📍 {job.location}\n"
        message += f"📊 Match: {match.match_score}%"

        if match.matched_skills:
            message += f"\n✅ Your skills: {', '.join(match.matched_skills)}"

        if match.missing_skills:
            message += f"\n💡 Learn: {', '.join(match.missing_skills)}"

        message += f"\n🔗 [Apply Now]({job.url})\n\n"
        message += "---\n\n"

    message += f"_Found {len(matches)} matches. Keep searching!_"
    return message


def format_jobs_message_simple(
    jobs: List[JobListing],
    max_jobs: int = 5
) -> str:
    """Format jobs as Telegram message (without resume matching)."""
    if not jobs:
        return "No jobs found. Try different keywords or broaden your search."

    message = "🔍 *Job Search Results*\n\n"

    for i, job in enumerate(jobs[:max_jobs], 1):
        message += f"*{i}. {job.title}*\n"
        message += f"🏢 {job.company}\n"
        message += f"📍 {job.location}"

        if job.salary:
            message += f"\n💰 {job.salary}"

        message += f"\n🔗 [Apply]({job.url})\n\n"
        message += "---\n\n"

    message += f"_Showing {min(max_jobs, len(jobs))} of {len(jobs)} jobs_"
    return message


def format_welcome_message(user_name: str = "there") -> str:
    """Format welcome message."""
    return (
        f"👋 *Welcome to AI Job Finder, {user_name}!*\n\n"
        f"I'll help you find your dream job using AI.\n\n"
        f"*How to use:*\n"
        f"• Type a job search like 'Python developer in Bangalore'\n"
        f"• Set your resume with /resume command\n"
        f"• Get daily alerts with /alerts\n\n"
        f"Let's find your next opportunity! 🚀"
    )


def format_help_message() -> str:
    """Format help message."""
    return (
        "📖 *Help*\n\n"
        "*Commands:*\n"
        "• /search [query] - Find jobs\n"
        "  Example: /search React developer remote\n\n"
        "• /resume [text] - Set your skills\n"
        "  Example: /resume Python, React, SQL\n\n"
        "• /alerts - Enable daily alerts\n"
        "• /stop - Disable alerts\n\n"
        "*Tips:*\n"
        "- Include location for local jobs\n"
        "- Add 'remote' for WFH positions\n"
        "- Specify experience level (fresher/senior)"
    )


def format_alert_message(
    matches: List[MatchResult],
    count: int = 5
) -> str:
    """Format daily alert message."""
    message = "🌟 *Daily Job Alert*\n\n"

    for i, match in enumerate(matches[:count], 1):
        job = match.job
        message += f"*{i}. {job.title}* @ {job.company}\n"
        message += f"   📊 {match.match_score}% match"
        if match.matched_skills:
            skills = ", ".join(match.matched_skills[:2])
            message += f" | ✅ {skills}"
        message += f"\n\n"

    message += f"_Plus {max(0, len(matches) - count)} more..._"
    return message


async def send_telegram_message(
    message: str,
    chat_id: str = None,
    token: str = None
) -> bool:
    """Send message via Telegram bot."""
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return False

    try:
        bot = Bot(token=token)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=" Markdown",
            disable_web_page_preview=True
        )
        return True
    except TelegramError:
        return False


async def send_job_alerts(
    matches: List[MatchResult],
    chat_id: str = None,
    token: str = None,
    custom_prompt: str = None
) -> bool:
    """Send job alerts via Telegram."""
    message = format_jobs_message(matches, custom_prompt=custom_prompt)
    return await send_telegram_message(message, chat_id, token)


async def send_job_alerts_simple(
    jobs: List[JobListing],
    chat_id: str = None,
    token: str = None
) -> bool:
    """Send job alerts via Telegram (without matching)."""
    message = format_jobs_message_simple(jobs)
    return await send_telegram_message(message, chat_id, token)


async def send_welcome(chat_id: str = None, token: str = None) -> bool:
    """Send welcome message."""
    message = format_welcome_message()
    return await send_telegram_message(message, chat_id, token)


async def send_help(chat_id: str = None, token: str = None) -> bool:
    """Send help message."""
    message = format_help_message()
    return await send_telegram_message(message, chat_id, token)