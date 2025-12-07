# consumer_client.py
import asyncio
import json
import random

import websockets

# receive same SESSION_ID as browser
SESSION_ID = "secret-session-id"  # same id used by browser


async def consumer():
    async with websockets.connect("ws://localhost:8765") as ws:
        # handshake
        hello = {"type": "hello", "role": "consumer", "session": SESSION_ID}
        await ws.send(json.dumps(hello))

        async def listen():
            async for msg in ws:
                print("[Consumer] Received HTML:", msg)

        async def send_commands():
            cmds = ["scroll-down", "scroll-up", "click()", "reload"]
            while True:
                cmd = random.choice(cmds)
                await ws.send(cmd)
                print("[Consumer] Sent command:", cmd)
                await asyncio.sleep(2)

        await asyncio.gather(listen(), send_commands())


asyncio.run(consumer())
