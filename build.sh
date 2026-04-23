#!/bin/bash
# Force Python 3.12 for Render deployment

# Create virtual environment with Python 3.12
virtualenv -p python3.12 venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers
playwright install chromium

# Run the app
uvicorn src.server:app --host 0.0.0.0 --port $PORT