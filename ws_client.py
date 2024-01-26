import traceback
import json
import asyncio
import time

import websockets

CONNECTION_URI = "ws://localhost:8765"


def serializer(obj):
    if not isinstance(obj, dict):
        raise TypeError("Expected type dict, got {0}".format(type(obj)))
    return json.dumps(obj)


async def send_request(websocket, request: str):
    try:
        await websocket.send(serializer({"request": request}))
        print(f"Sent request: {request}")
    except websockets.ConnectionClosedOK as e:
        print("Connection closed...\n"
              f"Err:\n{traceback.print_tb(e.__traceback__, 1)}")
        return None


async def get_response(websocket):
    try:
        return await websocket.recv()
    except websockets.ConnectionClosedOK as e:
        print("\nConnection closed...")
        traceback.print_tb(e.__traceback__)
        return None


async def main():
    time_a = time.time()

    async with websockets.connect(CONNECTION_URI, ping_interval=5) as websocket:
        try:
            await send_request(websocket, "Hello")
            async for message in websocket:
                print(f"Received response: {message}")

        except websockets.ConnectionClosedOK:
            print("Connection closed...")

        except websockets.ConnectionClosedError as e:
            traceback.print_tb(e.__traceback__)

    time_b = time.time()
    print(f"Time taken: {time_b - time_a}")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
