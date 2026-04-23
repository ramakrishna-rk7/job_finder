"""Time utilities for job freshness filtering."""

import re
from datetime import datetime, timedelta
from typing import Optional


def extract_hours(posted_time: str) -> int:
    """Convert posted time string to hours.
    
    Examples:
        "2 hours ago" -> 2
        "1 day ago" -> 24
        "3 days ago" -> 72
        "Just now" -> 0
        "30+ days ago" -> 999
    
    Args:
        posted_time: Time string like "2 hours ago", "1 day ago"
        
    Returns:
        Hours since posting (999 for very old/unknown)
    """
    if not posted_time:
        return 999
    
    text = posted_time.lower().strip()
    
    if "just" in text or "now" in text:
        return 0
    
    hour_match = re.search(r"(\d+)\s*hour", text)
    if hour_match:
        return int(hour_match.group(1))
    
    day_match = re.search(r"(\d+)\s*day", text)
    if day_match:
        return int(day_match.group(1)) * 24
    
    week_match = re.search(r"(\d+)\s*week", text)
    if week_match:
        return int(week_match.group(1)) * 24 * 7
    
    month_match = re.search(r"(\d+)\s*month", text)
    if month_match:
        return int(month_match.group(1)) * 24 * 30
    
    if "yesterday" in text:
        return 24
    
    if "today" in text:
        return 0
    
    if "+" in text or "ago" in text:
        num_match = re.search(r"(\d+)", text)
        if num_match:
            return int(num_match.group(1)) * 24
    
    return 999


def is_recent_job(posted_time: str, max_hours: int = 24) -> bool:
    """Check if job was posted within max_hours.
    
    Args:
        posted_time: Time string like "2 hours ago"
        max_hours: Maximum hours to consider recent (default: 24)
        
    Returns:
        True if job is recent enough
    """
    hours = extract_hours(posted_time)
    return hours <= max_hours


def format_freshness(hours: int) -> str:
    """Format hours as human-readable freshness string.
    
    Args:
        hours: Number of hours since posting
        
    Returns:
        Formatted string like "2 hours ago", "1 day ago"
    """
    if hours <= 0:
        return "Just now"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif hours < 48:
        return "1 day ago"
    elif hours < 24 * 7:
        days = hours // 24
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif hours < 24 * 30:
        weeks = hours // (24 * 7)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = hours // (24 * 30)
        return f"{months} month{'s' if months != 1 else ''} ago"


def normalize_posted_time(time_str: str) -> str:
    """Normalize posted time to standard format.
    
    Args:
        time_str: Raw time string from any source
        
    Returns:
        Normalized time string
    """
    if not time_str:
        return "Unknown"
    
    time_str = time_str.strip()
    hours = extract_hours(time_str)
    return format_freshness(hours)


def parse_indeed_time(time_str: str) -> int:
    """Parse Indeed-specific time format.
    
    Examples:
        "2 hours ago" -> 2
        "Hiring ongoing" -> 999
        "Today" -> 0
    """
    if not time_str:
        return 999
    
    text = time_str.lower()
    
    if "ongoing" in text or "active" in text:
        return 0
    
    if "today" in text:
        return 0
    
    return extract_hours(time_str)


def parse_naukri_time(time_str: str) -> int:
    """Parse Naukri-specific time format.
    
    Examples:
        "Posted 2 days ago" -> 48
        "Few hours ago" -> 1
        "Today" -> 0
    """
    if not time_str:
        return 999
    
    text = time_str.lower()
    
    if "few" in text and "hour" in text:
        return 1
    
    if "today" in text:
        return 0
    
    if "just" in text:
        return 0
    
    return extract_hours(time_str)


def parse_google_jobs_time(time_str: str) -> int:
    """Parse Google Jobs time format.
    
    Examples:
        "2 hours ago" -> 2
        "1 day ago" -> 24
        "Today" -> 0
    """
    return extract_hours(time_str)