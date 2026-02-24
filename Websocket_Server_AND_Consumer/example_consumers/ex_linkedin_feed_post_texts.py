# update-components-text relative update-components-update-v2__commentary

import asyncio
import json
import pprint
from asyncio.queues import Queue
from collections.abc import Mapping

import websockets

# receive same SESSION_ID as browser
SESSION_ID = "secret-session-id"  # same id used by browser


async def consumer():
    async with websockets.connect("ws://localhost:8765") as ws:
        # handshake
        hello = {"type": "hello", "role": "consumer", "session": SESSION_ID}
        await ws.send(json.dumps(hello))

        posts_data: set[str] = set()
        command_queue: Queue[Mapping[str, str | list[str] | float] | None] = Queue()

        posts_texts_selector = {
            "command": "sniff",
            "operation": "getAll",
            "selector": "update-components-text relative update-components-update-v2__commentary",
            "attribute": ["innerText"],
        }

        scroll_down_command = {
            "command": "sniff",
            "operation": "scrollDown",
            "selector": "#ember26",
            "selectIndex": 1,
            "attribute": "",
            "amount": 5000,
        }

        async def listen():
            prev_members_counts = 0
            async for msg in ws:
                # print("[Consumer] Received HTML:", msg)
                result = json.loads(msg)
                if result.get("messageType") == "sniffingResult" and (
                    data := result.get("data")
                ):
                    post_texts = data.get("innerText", [])
                    for post_text in post_texts:
                        if post_text not in posts_data:
                            # print(f"[Consumer] New post found: {post_text}")
                            posts_data.add(post_text)

                    if prev_members_counts == len(posts_data):
                        print(
                            "[Consumer] No new posts found in this iteration. Stopping further scrolls."
                        )
                        await ws.close()
                        await command_queue.put(None)  # signal to stop sending commands
                        return
                    prev_members_counts = len(posts_data)

        async def send_commands():
            await asyncio.sleep(2)  # wait for 2 seconds before starting
            await command_queue.put(posts_texts_selector)
            while True:
                command = await command_queue.get()
                if command is None:
                    print("[Consumer] Stopping command sender.")
                    break
                await ws.send(json.dumps(command))
                await asyncio.sleep(2)  # wait for 2 seconds between commands
                if command == posts_texts_selector:
                    await command_queue.put(scroll_down_command)
                elif command == scroll_down_command:
                    await command_queue.put(posts_texts_selector)

        await asyncio.gather(listen(), send_commands())

        print(f"[Consumer] Scraping completed. {len(posts_data)} unique posts found.")
        return posts_data


try:
    posts_data = asyncio.run(consumer())
    print(f"[Consumer] Scraping completed. {len(posts_data)} unique posts found.")
    pprint.pprint(posts_data)
except KeyboardInterrupt:
    print("[Consumer] Interrupted by user, exiting...")
except Exception as e:
    print(f"[Consumer] Error occurred: {e}")
