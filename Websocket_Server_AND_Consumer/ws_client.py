import asyncio
from datetime import datetime

from websockets.asyncio.client import connect

SERVER_URI = "ws://localhost:8765"


async def hello():
    async with connect(SERVER_URI) as websocket:
        dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hello_text = f"Hello at {dt_str}"

        await websocket.send(hello_text)
        print(f"> {hello_text}")

        greeting = await websocket.recv()
        print(f"< {greeting!r}")


if __name__ == "__main__":
    asyncio.run(hello())
