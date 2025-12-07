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
            cmds = [
                {
                    "command": "sniff",
                    "operation": "getAll",
                    "selector": "div[itemprop=author]>a",
                    "attribute": "innerText",
                },
            ]
            command_iterator = iter(cmds)
            while next_cmd := next(command_iterator, None):
                print(next_cmd)
                cmd = next_cmd
                await ws.send(json.dumps(cmd))
                print("[Consumer] Sent command:", cmd)

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        await asyncio.gather(listen(), send_commands())


asyncio.run(consumer())
