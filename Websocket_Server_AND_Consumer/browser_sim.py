# browser_client.py
import asyncio
import json
import random

import websockets

# this can be defined in browser and via API request to server we can spin up WS consumer sessions
SESSION_ID = "secret-session-id"  # same id used by consumer


async def browser():
    async with websockets.connect("ws://localhost:8765") as ws:
        # handshake
        hello = {"type": "hello", "role": "browser", "session": SESSION_ID}
        await ws.send(json.dumps(hello))

        async def send_html():
            while True:
                html = f"<html><body>frame={random.randint(0, 999)}</body></html>"
                await ws.send(html)
                print("[Browser] Sent HTML:", html)
                await asyncio.sleep(1)

        async def listen():
            async for msg in ws:
                print("[Browser] Received command:", msg)

        await asyncio.gather(send_html(), listen())


asyncio.run(browser())
