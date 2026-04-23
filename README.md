# AI Job Finder

A smart, multi-source job search assistant with Telegram integration built with Python, FastAPI, and AI.

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot-Blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## Features

- **Multi-Source Scraping** - Jobs from Indeed, Naukri, LinkedIn, and Google Jobs
- **AI-Powered Ranking** - Scores jobs by relevance, freshness, and skills
- **Telegram Bot** - Search jobs directly from Telegram
- **Time Filtering** - Shows only recent jobs (≤24 hours)
- **Resume Matching** - Match jobs with your skills
- **Context Memory** - Remembers your preferences

---

## Demo

Search for jobs via Telegram:

```
/search Python developer fresher India
```

Or just send a message:
```
python developer fresher India
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python |
| AI | HuggingFace (DeepSeek-R1) / Groq |
| Scraping | Playwright + httpx |
| Bot | python-telegram-bot |
| Database | JSON file storage |

---

## Quick Start

### Local Setup

```bash
# Clone the repo
git clone https://github.com/ramakrishna-rk7/job_finder.git

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
python -m src.server
```

### Run Telegram Bot

```bash
python -m src.bot
```

### Or run both

```bash
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

---

## Deployment

### Render (Recommended)

1. Create a **Web Service** on [Render](https://render.com)
2. Connect your GitHub repository
3. Configure:
   - **Runtime:** Python 3.12
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.server:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `HF_TOKEN`
5. Deploy!

### Set Telegram Webhook

After deployment, set the webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<YOUR_APP>.onrender.com/webhook"
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | Yes |
| `HF_TOKEN` | HuggingFace token for AI | Optional |
| `GROQ_API_KEY` | Groq API key (fallback) | Optional |
| `DEFAULT_MAX_JOBS` | Max jobs to fetch (default: 20) | No |
| `DEFAULT_FRESHNESS_HOURS` | Hours filter (default: 24) | No |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status |
| `/health` | GET | Health check |
| `/search` | POST | Job search API |
| `/webhook` | POST | Telegram webhook |
| `/send-alert` | POST | Manual alert |

### Search API Example

```bash
curl -X POST https://job-finder.onrender.com/search \
  -H "Content-Type: application/json" \
  -d '{"prompt": "python developer fresher India"}'
```

---

## Project Structure

```
job_finder/
├── src/
│   ├── agents/           # AI agents (parser, ranker, filter)
│   ├── config/           # Settings
│   ├── schemas/         # Data models
│   ├── services/         # Storage, memory, Telegram
│   ├── tools/
│   │   └── scrapers/    # Job scrapers (Indeed, Naukri, etc.)
│   ├── utils/           # Time utilities
│   ├── bot.py           # Telegram bot
│   ├── server.py       # FastAPI server
│   ├── job_search.py   # Search pipeline
│   └── main.py          # CLI entry
├── data/                # JSON storage
├── requirements.txt    # Python dependencies
└── runtime.txt          # Python version
```

---

## Commands

### Telegram Bot

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Help |
| `/search <query>` | Search jobs |
| `/resume <skills>` | Set your skills |
| `/alerts` | Enable daily alerts |
| Any text | Auto-search |

### CLI

```bash
# Search jobs
python -m src.main "Python developer remote"

# With resume
python -m src.main "Python developer" --resume resume.txt

# List saved jobs
python -m src.main --list
```

---

## License

MIT License - feel free to use!

---

## Credits

- [CrewAI](https://crewai.com) - AI agent framework
- [HuggingFace](https://huggingface.co) - DeepSeek-R1 model
- [Indeed](https://indeed.com) - Job listings
- [Naukri](https://naukri.com) - India job listings

---

## Support

For issues or questions, please open a GitHub issue.

---

**Built with ❤️ using Python, FastAPI, and AI**