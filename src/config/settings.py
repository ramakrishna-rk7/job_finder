"""Configuration settings for Job Finder."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "deepseek-ai/DeepSeek-R1")

JOBS_FILE_PATH = os.getenv("JOBS_FILE_PATH", str(DATA_DIR / "jobs.json"))
RESUME_FILE_PATH = os.getenv("RESUME_FILE_PATH", str(DATA_DIR / "resume.txt"))
USER_PREFS_FILE_PATH = os.getenv("USER_PREFS_FILE_PATH", str(DATA_DIR / "user_prefs.json"))

DEFAULT_MAX_JOBS = int(os.getenv("DEFAULT_MAX_JOBS", "20"))
DEFAULT_MIN_MATCH_SCORE = int(os.getenv("DEFAULT_MIN_MATCH_SCORE", "50"))
DEFAULT_FRESHNESS_HOURS = int(os.getenv("DEFAULT_FRESHNESS_HOURS", "24"))

SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "60"))

LLM_MODEL = os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
MAX_CONCURRENT_SOURCES = int(os.getenv("MAX_CONCURRENT_SOURCES", "3"))

USE_HF = bool(HF_TOKEN and HF_MODEL)


def get_llm_config():
    """Return LLM configuration for CrewAI agents."""
    return {
        "model": LLM_MODEL if not USE_HF else HF_MODEL,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)