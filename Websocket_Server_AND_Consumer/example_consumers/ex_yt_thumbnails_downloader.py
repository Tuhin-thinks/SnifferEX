# consumer_client.py
import asyncio
import json
import pprint

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
                # print("[Consumer] Received HTML:", msg)
                pprint.pprint(json.loads(msg))

        async def send_commands():
            

            selector_thumbnail_images = {
                "command": "sniff",
                "operation": "getAll",
                "selector": ".ytThumbnailViewModelImage>img.ytCoreImageLoaded",
                # src for the thumbnail image URL
                "attribute": ["src"],
            }
            selector_video_urls = {
                "command": "sniff",
                "operation": "getAll",
                "selector": "a.yt-lockup-view-model__content-image",
                # innerText for the video time; href for the video URL
                "attribute": ["href"],
            }

            scrolling_command = {
                "command": "scroll",
                "operation": "executeScript",
                "selector": "",
                "attribute": [],
                "script": "window.dispatchEvent(new WheelEvent(\"wheel\", { deltaY: 400 }));",
            }

            cmds = [
                selector_thumbnail_images,
                selector_video_urls,
                scrolling_command,
            ] * 20
            command_iterator = iter(cmds)
            while next_cmd := next(command_iterator, None):
                cmd = next_cmd
                await ws.send(json.dumps(cmd))

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        await asyncio.gather(listen(), send_commands())


asyncio.run(consumer())
