"""Telegram service for notifications."""

import asyncio
from typing import List, Optional
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode

from ..schemas.models import MatchResult, JobListing
from ..config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramService:
    """Service for Telegram bot operations."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None

    async def initialize(self):
        """Initialize bot connection."""
        if self.token:
            self.bot = Bot(token=self.token)

    async def close(self):
        """Close bot connection."""
        pass

    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        disable_web_preview: bool = True
    ) -> bool:
        """Send a message."""
        if not self.bot or not self.chat_id:
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_preview
            )
            return True
        except TelegramError:
            return False

    def format_job_matches(
        self,
        matches: List[MatchResult],
        max_count: int = 5,
        custom_header: str = None
    ) -> str:
        """Format matched jobs as message."""
        if not matches:
            return "No matching jobs found for your profile. Consider expanding your skill set!"

        header = custom_header or "🎯 *Your Personalized Job Matches*"
        message = f"{header}\n\n"

        for i, match in enumerate(matches[:max_count], 1):
            job = match.job
            message += f"*{i}. {job.title}* at {job.company}\n"
            message += f"📍 {job.location}\n"
            message += f"📊 Match: {match.match_score}%"

            if match.matched_skills:
                message += f"\n✅ Your skills: {', '.join(match.matched_skills[:3])}"

            if match.missing_skills:
                message += f"\n💡 Gap: {', '.join(match.missing_skills[:2])}"

            message += f"\n🔗 [Apply]({job.url})\n\n"
            message += "---\n\n"

        remaining = len(matches) - max_count
        if remaining > 0:
            message += f"_Plus {remaining} more matches..._"

        return message

    def format_job_list(
        self,
        jobs: List[JobListing],
        max_count: int = 5,
        custom_header: str = None
    ) -> str:
        """Format job list as message."""
        if not jobs:
            return "No jobs found. Try different keywords!"

        header = custom_header or "🔍 *Job Search Results*"
        message = f"{header}\n\n"

        for i, job in enumerate(jobs[:max_count], 1):
            message += f"*{i}. {job.title}*\n"
            message += f"🏢 {job.company}\n"
            message += f"📍 {job.location}"

            if job.salary:
                message += f"\n💰 {job.salary}"

            if job.posted_date:
                message += f"\n🕐 {job.posted_date}"

            message += f"\n🔗 [Apply]({job.url})\n\n"
            message += "---\n\n"

        remaining = len(jobs) - max_count
        if remaining > 0:
            message += f"_Showing {max_count} of {len(jobs)} jobs_"

        return message

    def format_daily_alert(
        self,
        matches: List[MatchResult],
        count: int = 5
    ) -> str:
        """Format daily alert message."""
        message = "🌟 *Good Morning! Daily Jobs Inside* 🌟\n\n"

        for i, match in enumerate(matches[:count], 1):
            job = match.job
            message += f"_{* i}. {job.title}* @ {job.company}\n"
            message += f"   📊 {match.match_score}% match"
            if match.matched_skills:
                skills = ", ".join(match.matched_skills[:2])
                message += f" | ✅ {skills}"
            message += f"\n\n"

        remaining = len(matches) - count
        if remaining > 0:
            message += f"_...and {remaining} more!_"

        message += "\n💪 Keep applying! You'll land something great."
        return message

    def format_welcome(self, user_name: str = "there") -> str:
        """Format welcome message."""
        return (
            f"👋 *Welcome to AI Job Finder, {user_name}!*\n\n"
            f"I'll help you discover your dream job using AI.\n\n"
            f"*How it works:*\n"
            f"• Search jobs naturally\n"
            f"• Get personalized matches\n"
            f"• Receive daily alerts\n\n"
            f"Ready? Let's start! 🚀"
        )

    def format_help(self) -> str:
        """Format help message."""
        return (
            "📖 *Help Guide*\n\n"
            "*Commands:*\n"
            "• /search [query] - Find jobs\n"
            "• /resume [text] - Set skills\n"
            "• /alerts - Daily digest\n"
            "• /stop - Pause alerts\n\n"
            "*Search Tips:*\n"
            "- 'remote' for WFH\n"
            "- Add city for local\n"
            "- Include experience level"
        )

    def format_no_results(self) -> str:
        """Format no results message."""
        return (
            "😕 No jobs found.\n\n"
            "Try:\n"
            "- Different keywords\n"
            "- Broader location\n"
            "- More skills in /resume"
        )

    def format_error(self, error: str) -> str:
        """Format error message."""
        return f"⚠️ *Oops!* Something went wrong.\n\n_{error}_\n\nTry again later."

    def format_set_resume(self, skills: str) -> str:
        """Format resume set confirmation."""
        return (
            f"✅ *Resume Updated!*\n\n"
            f"Skills: {skills}\n\n"
            f"I'll use these to find better matches!"
        )

    def format_alerts_enabled(self, time: str = "09:00") -> str:
        """Format alerts enabled message."""
        return (
            f"🔔 *Daily Alerts Enabled!*\n\n"
            f"You'll get job alerts at *{time}* daily.\n\n"
            f"Keep your resume updated for best matches!"
        )

    def format_alerts_disabled(self) -> str:
        """Format alerts disabled message."""
        return "🔕 *Alerts Disabled*\n\nNo more daily job alerts. Use /search to find jobs anytime."

    async def send_job_matches(
        self,
        matches: List[MatchResult],
        max_count: int = 5,
        custom_header: str = None
    ) -> bool:
        """Send job matches notification."""
        message = self.format_job_matches(matches, max_count, custom_header)
        return await self.send_message(message)

    async def send_job_list(
        self,
        jobs: List[JobListing],
        max_count: int = 5,
        custom_header: str = None
    ) -> bool:
        """Send job list notification."""
        message = self.format_job_list(jobs, max_count, custom_header)
        return await self.send_message(message)

    async def send_daily_alert(self, matches: List[MatchResult], count: int = 5) -> bool:
        """Send daily alert notification."""
        message = self.format_daily_alert(matches, count)
        return await self.send_message(message)

    async def send_welcome(self, user_name: str = "User") -> bool:
        """Send welcome message."""
        message = self.format_welcome(user_name)
        return await self.send_message(message)

    async def send_help(self) -> bool:
        """Send help message."""
        message = self.format_help()
        return await self.send_message(message)


async def send_telegram_notification(
    message: str,
    token: str = None,
    chat_id: str = None
) -> bool:
    """Convenience function to send notification."""
    service = TelegramService(token, chat_id)
    await service.initialize()
    result = await service.send_message(message)
    await service.close()
    return result