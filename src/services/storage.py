"""Storage service for jobs and user preferences."""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..schemas.models import JobListing, UserPreferences, SearchResult, StructuredQuery
from ..config.settings import (
    JOBS_FILE_PATH,
    USER_PREFS_FILE_PATH,
    ensure_data_dir,
    DEFAULT_MAX_JOBS,
    DEFAULT_MIN_MATCH_SCORE
)


def load_all_jobs() -> List[JobListing]:
    """Load all saved jobs."""
    path = Path(JOBS_FILE_PATH)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [JobListing(**job) for job in data]
    except (json.JSONDecodeError, TypeError):
        return []


def save_all_jobs(jobs: List[JobListing]) -> None:
    """Save all jobs."""
    ensure_data_dir()
    path = Path(JOBS_FILE_PATH)
    data = [job.model_dump() for job in jobs]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_jobs(jobs: List[JobListing], max_jobs: int = None) -> List[JobListing]:
    """Add new jobs, keeping most recent."""
    max_jobs = max_jobs or DEFAULT_MAX_JOBS
    existing = load_all_jobs()
    existing_urls = {job.url for job in existing}

    new_jobs = [job for job in jobs if job.url not in existing_urls]
    all_jobs = existing + new_jobs

    all_jobs.sort(key=lambda x: x.posted_date or "", reverse=True)
    all_jobs = all_jobs[:max_jobs]

    save_all_jobs(all_jobs)
    return all_jobs


def get_jobs_by_keyword(keyword: str) -> List[JobListing]:
    """Filter jobs by keyword."""
    jobs = load_all_jobs()
    keyword_lower = keyword.lower()
    return [
        job for job in jobs
        if keyword_lower in job.title.lower()
        or keyword_lower in job.company.lower()
        or keyword_lower in job.description.lower()
    ]


def delete_job(url: str) -> bool:
    """Delete a job by URL."""
    jobs = load_all_jobs()
    original_count = len(jobs)
    jobs = [job for job in jobs if job.url != url]

    if len(jobs) < original_count:
        save_all_jobs(jobs)
        return True
    return False


def load_user_preferences(user_id: str) -> Optional[UserPreferences]:
    """Load user preferences."""
    path = Path(USER_PREFS_FILE_PATH)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if user_id in data:
            return UserPreferences(**data[user_id])
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def save_user_preferences(prefs: UserPreferences) -> None:
    """Save user preferences."""
    ensure_data_dir()
    path = Path(USER_PREFS_FILE_PATH)

    all_prefs = {}
    if path.exists():
        try:
            all_prefs = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            all_prefs = {}

    all_prefs[prefs.user_id] = prefs.model_dump()

    path.write_text(json.dumps(all_prefs, indent=2, ensure_ascii=False), encoding="utf-8")


def get_all_users() -> List[UserPreferences]:
    """Get all saved users."""
    path = Path(USER_PREFS_FILE_PATH)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [UserPreferences(**prefs) for prefs in data.values()]
    except (json.JSONDecodeError, TypeError):
        return []


def clear_old_jobs(days: int = 30) -> int:
    """Remove jobs older than specified days."""
    jobs = load_all_jobs()
    if not jobs:
        return 0

    original_count = len(jobs)
    jobs = [job for job in jobs if job.posted_date]

    save_all_jobs(jobs)
    return original_count - len(jobs)