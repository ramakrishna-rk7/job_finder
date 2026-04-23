"""Telegram bot poller - with instant feedback."""

import asyncio
import os
import sys
import httpx

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

TOKEN = '8723909515:AAGn_5Da8T6z7QULdpQRbZ30vvVGlcmnxAc'

SEARCHING_MSG = """Searching for jobs... 🔍

Please wait while I find the best job links for you!"""

SEARCHING_MSG_SHORT = "Searching... ⏳"


async def send_message(chat_id: str, text: str) -> bool:
    """Send Telegram message."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json().get("ok", False)


async def poll():
    """Poll for updates."""
    from src.server import process_job_search, format_job_message
    
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    offset = 0
    
    print("Bot polling started...")
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json={"timeout": 30, "offset": offset})
                data = r.json()
                
                if data.get("ok"):
                    updates = data.get("result", [])
                    
                    for u in updates:
                        msg = u.get("message", {})
                        txt = msg.get("text", "")
                        chat = str(msg.get("chat", {}).get("id", ""))
                        
                        if txt and not txt.startswith("/"):
                            print(f"Request: {txt}")
                            
                            # 1. INSTANT - Send "searching" message
                            await client.post(
                                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                json={"chat_id": chat, "text": SEARCHING_MSG_SHORT}
                            )
                            
                            # 2. Then process the search
                            jobs, _ = await process_job_search(txt, max_results=3)
                            resp = format_job_message(jobs)
                            
                            # 3. Send the results
                            await client.post(
                                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                json={"chat_id": chat, "text": resp}
                            )
                            
                            print(f"Sent to {chat}")
                            
                            
                            # Mark as read
                            offset = u.get("update_id", 0) + 1
                            await client.post(url, json={"offset": offset})
        except Exception as e:
            print(f"Error: {e}")
        
        await asyncio.sleep(2)


if __name__ == "__main__":
    print("Starting bot...")
    asyncio.run(poll())