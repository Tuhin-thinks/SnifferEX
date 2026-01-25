"""This example can scrape all users who liked an Instagram post. You have to keep the likes dashboard open."""
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

        unique_likers = set()
        command_queue: Queue[Mapping[str, str | list[str] | float] | None] = Queue()

        scrape_likers_command = {
            "command": "sniff",
            "operation": "getAll",
            "selector": 'div[role="dialog"] a[role="link"]:nth-child(1)',
            "attribute": ["innerText", "href"],
        }

        scroll_down_command = {
            "command": "sniff",
            "operation": "scrollDown",
            "selector": 'div[role="dialog"]',
            "attribute": "",
            "amount": 1000,
        }

        async def listen():
            prev_likers_counts = 0
            async for msg in ws:
                # print("[Consumer] Received HTML:", msg)
                result = json.loads(msg)
                pprint.pprint(result)
                if result.get("messageType") == "sniffingResult" and (
                    data := result.get("data")
                ):
                    likers = data.get("innerText", [])
                    hrefs = data.get("href", [])
                    for liker, href in zip(likers, hrefs):
                        if liker not in unique_likers:
                            unique_likers.add(liker)
                            print(f"[Consumer] New liker found: {liker} - {href}")

                    if prev_likers_counts == len(unique_likers):
                        print(
                            "[Consumer] No new likers found in this iteration. Stopping further scrolls."
                        )
                        await ws.close()
                        await command_queue.put(None)  # signal to stop sending commands
                        return
                    prev_likers_counts = len(unique_likers)
                    print(
                        f"[Consumer] Total unique likers collected: {len(unique_likers)}"
                    )
                    # add scroll down command to queue, and scrape likers again; if no new likers found after several iterations, we can stop
                    await command_queue.put(scroll_down_command)
                    await command_queue.put(scrape_likers_command)

                    print("[Consumer] Enqueued scroll down and scrape likers commands.")

        async def send_commands():
            command_queue.put_nowait(scrape_likers_command)
            while next_cmd := await command_queue.get():
                if not next_cmd:
                    break
                cmd = next_cmd
                await ws.send(json.dumps(cmd))

                if cmd["operation"] == "scrollDown":
                    await asyncio.sleep(2.0)  # wait between commands

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        await asyncio.gather(listen(), send_commands())

        return unique_likers


try:
    unique_likers = asyncio.run(consumer())
    print(f"Total unique likers collected: {len(unique_likers)}")
    print(unique_likers)
except KeyboardInterrupt:
    print("Consumer stopped by user.")
