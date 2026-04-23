"""File tools for reading resume and saving jobs."""

import json
from pathlib import Path
from typing import List, Optional

from ..schemas.models import JobListing, UserPreferences
from ..config.settings import (
    RESUME_FILE_PATH,
    JOBS_FILE_PATH,
    USER_PREFS_FILE_PATH,
    ensure_data_dir
)


def read_resume(file_path: Optional[str] = None) -> str:
    """Read resume from text file."""
    path = Path(file_path or RESUME_FILE_PATH)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_resume(resume_text: str, file_path: Optional[str] = None) -> None:
    """Save resume to text file."""
    ensure_data_dir()
    path = Path(file_path or RESUME_FILE_PATH)
    path.write_text(resume_text, encoding="utf-8")


def load_jobs() -> List[JobListing]:
    """Load jobs from JSON file."""
    path = Path(JOBS_FILE_PATH)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [JobListing(**job) for job in data]


def save_jobs(jobs: List[JobListing]) -> None:
    """Save jobs to JSON file."""
    ensure_data_dir()
    path = Path(JOBS_FILE_PATH)
    data = [job.model_dump() for job in jobs]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jobs(jobs: List[JobListing]) -> None:
    """Append jobs to existing JSON file."""
    existing = load_jobs()
    existing_urls = {job.url for job in existing}

    new_jobs = [job for job in jobs if job.url not in existing_urls]
    all_jobs = existing + new_jobs

    save_jobs(all_jobs)


def load_user_prefs(user_id: str) -> Optional[UserPreferences]:
    """Load user preferences."""
    path = Path(USER_PREFS_FILE_PATH)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if user_id in data:
        return UserPreferences(**data[user_id])
    return None


def save_user_prefs(prefs: UserPreferences) -> None:
    """Save user preferences."""
    ensure_data_dir()
    path = Path(USER_PREFS_FILE_PATH)

    all_prefs = {}
    if path.exists():
        all_prefs = json.loads(path.read_text(encoding="utf-8"))

    all_prefs[prefs.user_id] = prefs.model_dump()

    path.write_text(json.dumps(all_prefs, indent=2, ensure_ascii=False), encoding="utf-8")