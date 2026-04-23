"""Main entry point for Job Finder."""

import asyncio
import argparse
import os
import sys
from typing import Optional

from .schemas.models import SearchResult
from .config.settings import DEFAULT_MAX_JOBS, DEFAULT_MIN_MATCH_SCORE
from .tools.file_tools import read_resume
from .services.storage import load_all_jobs, get_jobs_by_keyword
from .job_search import run_prompt_search, run_quick_search
from .agents.notifier import send_job_alerts, send_job_alerts_simple


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Job Finder - Prompt-based job search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main "Python developer remote jobs"
  python -m src.main "AI/ML fresher in India"
  python -m src.main "React internships" --resume resume.txt
  python -m src.main "Senior Data Scientist Bangalore" --notify
        """
    )
    parser.add_argument("prompt", nargs="?", help="Job search prompt")
    parser.add_argument("--resume", "-r", help="Path to resume file")
    parser.add_argument("--max", "-m", type=int, default=DEFAULT_MAX_JOBS, help="Max results")
    parser.add_argument("--notify", "-n", action="store_true", help="Send Telegram notification")
    parser.add_argument("--config", "-c", help="Path to .env file")
    parser.add_argument("--list", "-l", action="store_true", help="List saved jobs")
    parser.add_argument("--keyword", "-k", help="Filter saved jobs by keyword")
    parser.add_argument("--simple", "-s", action="store_true", help="Use simple parsing (no AI)")
    parser.add_argument("--version", "-v", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("AI Job Finder v1.0.0")
        return

    if args.config:
        from dotenv import load_dotenv
        load_dotenv(args.config)

    if args.list:
        jobs = load_all_jobs()
        if not jobs:
            print("No saved jobs.")
            return
        print(f"\n📋 Saved Jobs ({len(jobs)}):\n")
        for i, job in enumerate(jobs[:20], 1):
            print(f"{i}. {job.title}")
            print(f"   {job.company} | {job.location}")
            if job.url:
                print(f"   {job.url}")
            print()
        return

    if args.keyword:
        jobs = get_jobs_by_keyword(args.keyword)
        if not jobs:
            print(f"No jobs found for '{args.keyword}'")
            return
        print(f"\n📋 Jobs matching '{args.keyword}' ({len(jobs)}):\n")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.title} at {job.company}")
        return

    if not args.prompt:
        parser.print_help()
        print("\n" + "="*50)
        print("Quick Start:")
        print('  python -m src.main "Python developer"')
        print('  python -m src.main "AI/ML fresher in India"')
        print('  python -m src.main "React remote" --resume resume.txt --notify')
        print("="*50)
        return

    resume_text = None
    if args.resume and os.path.exists(args.resume):
        resume_text = read_resume(args.resume)
        print(f"📄 Loaded resume from {args.resume}")

    result = asyncio.run(run_prompt_search(
        args.prompt,
        resume_text,
        args.max,
        args.notify,
        use_ai_parsing=not args.simple
    ))

    print("\n" + "="*50)
    print("📊 RESULTS")
    print("="*50)

    print(f"\n🔍 Search: {args.prompt}")
    print(f"📦 Found: {result.filtered_count} jobs")

    if result.matched_jobs:
        print(f"\n🎯 Top Matches (score >= {DEFAULT_MIN_MATCH_SCORE}%):")
        for i, match in enumerate(result.matched_jobs[:5], 1):
            print(f"\n{i}. {match.job.title}")
            print(f"   🏢 {match.job.company}")
            print(f"   📍 {match.job.location}")
            print(f"   📊 Match: {match.match_score}%")
            if match.matched_skills:
                print(f"   ✅ Skills: {', '.join(match.matched_skills)}")
            if match.missing_skills:
                print(f"   💡 Gap: {', '.join(match.missing_skills)}")
            if match.job.url:
                print(f"   🔗 {match.job.url}")
    else:
        print(f"\n📋 Jobs Found:")
        for i, job in enumerate(result.jobs[:5], 1):
            print(f"\n{i}. {job.title}")
            print(f"   🏢 {job.company}")
            print(f"   📍 {job.location}")
            if job.url:
                print(f"   🔗 {job.url}")

    if result.telegram_sent:
        print("\n✅ Notification sent!")

    print("\n" + "="*50)


if __name__ == "__main__":
    main()