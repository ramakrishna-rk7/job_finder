"""Telegram bot poller."""

import asyncio
import os
import sys
import httpx

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server import process_job_search, format_job_message

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8723909515:AAGn_5Da8T6z7QULdpQRbZ30vvVGlcmnxAc")

LAST_OFFSET = 0


async def send_message(chat_id: str, text: str) -> bool:
    """Send message to user."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json().get("ok", False)


async def process_update(update: dict) -> None:
    """Process single update."""
    global LAST_OFFSET
    
    msg = update.get("message", {})
    text = msg.get("text", "")
    chat_id = str(msg.get("chat", {}).get("id", ""))
    
    if not text or text.startswith("/"):
        return
    
    # Show typing action
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"}
        )
    
    # Process and respond
    jobs, _ = await process_job_search(text, max_results=3)
    response = format_job_message(jobs)
    
    await send_message(chat_id, response)
    print(f"Replied: {text[:20]} -> {chat_id}")


async def poll_loop():
    """Poll for updates."""
    global LAST_OFFSET
    
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    print("Polling for messages...")
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                payload = {"timeout": 30}
                if LAST_OFFSET:
                    payload["offset"] = LAST_OFFSET
                
                r = await client.post(url, json=payload)
                data = r.json()
                
                if data.get("ok"):
                    updates = data.get("result", [])
                    
                    for update in updates:
                        await process_update(update)
                        LAST_OFFSET = update.get("update_id", 0) + 1
                
        except Exception as e:
            print(f"Error: {e}")
        
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(poll_loop())