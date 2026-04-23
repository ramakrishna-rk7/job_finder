"""Telegram bot handler for AI Job Finder."""

import os
import asyncio
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    PicklePersistence
)

from .config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .schemas.models import UserPreferences
from .tools.file_tools import save_resume, read_resume
from .services.storage import (
    load_user_preferences,
    save_user_preferences,
    get_all_users
)
from .job_search import run_prompt_search
from .agents.notifier import format_welcome_message, format_help_message


class JobFinderBot:
    """Telegram bot handler for job finder."""

    def __init__(self, token: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.app = None
        self.user_sessions = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            format_welcome_message(update.effective_user.first_name),
            parse_mode="Markdown"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            format_help_message(),
            parse_mode="Markdown"
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text(
                "Usage: /search <job query>\n"
                "Example: /search Python developer remote"
            )
            return

        await update.message.reply_text(f"🔍 Searching for: {query}")

        try:
            result = await run_prompt_search(query, max_results=5)

            if result.ranked_jobs:
                message = "🔥 *Latest Jobs*\n\n"
                for i, ranked_job in enumerate(result.ranked_jobs[:5], 1):
                    job = ranked_job.job
                    message += f"*{i}. {job.title}*\n"
                    message += f"   🏢 {job.company}\n"
                    message += f"   🕐 {job.posted_time or 'Unknown'}\n"
                    message += f"   📍 {job.location}\n"
                    if job.url:
                        message += f"   🔗 [Apply]({job.url})\n"
                    message += "\n"
            elif result.matched_jobs:
                message = "🎯 *Your Matches*\n\n"
                for i, match in enumerate(result.matched_jobs[:5], 1):
                    job = match.job
                    message += f"*{i}. {job.title}* @ {job.company}\n"
                    message += f"📍 {job.location} | 📊 {match.match_score}%\n"
                    if match.matched_skills:
                        message += f"✅ {', '.join(match.matched_skills[:2])}\n"
                    message += f"[Apply]({job.url})\n\n"
            else:
                message = f"Found {result.filtered_count} jobs:\n\n"
                for i, job in enumerate(result.jobs[:5], 1):
                    message += f"*{i}. {job.title}* @ {job.company}\n"
                    message += f"🕐 {job.posted_time or 'Unknown'}\n"
                    message += f"📍 {job.location}\n[Apply]({job.url})\n\n"

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command."""
        user_id = str(update.effective_user.id)
        resume_text = " ".join(context.args)

        if not resume_text:
            current = read_resume()
            if current:
                await update.message.reply_text(
                    f"📄 Current resume:\n\n{current[:500]}"
                )
            else:
                await update.message.reply_text("No resume saved. Use /resume <text>")
            return

        save_resume(resume_text)
        prefs = load_user_preferences(user_id) or UserPreferences(user_id=user_id)
        prefs.resume_text = resume_text
        save_user_preferences(prefs)

        await update.message.reply_text("✅ Resume saved!")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command."""
        user_id = str(update.effective_user.id)

        prefs = load_user_preferences(user_id) or UserPreferences(user_id=user_id)
        prefs.notify_daily = True
        save_user_preferences(prefs)

        await update.message.reply_text(
            "🔔 Daily alerts enabled!\n"
            "You'll receive job alerts daily at 9:00 AM."
        )

    async def stop_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        user_id = str(update.effective_user.id)

        prefs = load_user_preferences(user_id)
        if prefs:
            prefs.notify_daily = False
            save_user_preferences(prefs)

        await update.message.reply_text("Alerts disabled.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages as job search prompts."""
        query = update.message.text

        if query.startswith("/"):
            return

        await update.message.reply_text(f"Searching: {query}")

        try:
            result = await run_prompt_search(query, max_results=5)
            
            # First try ranked jobs
            if result.ranked_jobs:
                message = "*Latest Jobs:*\n\n"
                for i, ranked_job in enumerate(result.ranked_jobs[:5], 1):
                    job = ranked_job.job
                    message += f"{i}. {job.title}\n"
                    message += f"   Company: {job.company}\n"
                    message += f"   Time: {job.posted_time or 'Unknown'}\n"
                    message += f"   Location: {job.location}\n"
                    message += f"   Link: {job.url}\n\n"
            # Then matched jobs
            elif result.matched_jobs:
                message = "*Your Matches:*\n\n"
                for i, match in enumerate(result.matched_jobs[:5], 1):
                    job = match.job
                    message += f"{i}. {job.title}\n"
                    message += f"   {job.company} | {job.location}\n"
                    message += f"   Score: {match.match_score}%\n"
                    message += f"   Link: {job.url}\n\n"
            # Then regular jobs
            elif result.jobs:
                message = "*Results:*\n\n"
                for i, job in enumerate(result.jobs[:5], 1):
                    message += f"{i}. {job.title}\n"
                    message += f"   Company: {job.company}\n"
                    message += f"   Time: {job.posted_time or 'Unknown'}\n"
                    message += f"   Location: {job.location}\n"
                    message += f"   Link: {job.url}\n\n"
            else:
                message = "No jobs found. Try different keywords."

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        print(f"Error: {context.error}")

    def run(self):
        """Run the bot."""
        from telegram.ext import Application

        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("resume", self.resume_command))
        self.app.add_handler(CommandHandler("alerts", self.alerts_command))
        self.app.add_handler(CommandHandler("stop", self.stop_alerts))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))

        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def run_bot(token: str = None):
    """Run the Telegram bot."""
    token = token or TELEGRAM_BOT_TOKEN
    if not token:
        print("No TELEGRAM_BOT_TOKEN configured")
        return

    bot = JobFinderBot(token)
    bot.run()


if __name__ == "__main__":
    run_bot()