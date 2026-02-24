"""This example can scrape all users who liked an Instagram post. You have to keep the likes dashboard open."""

import asyncio
import json
import pprint
from asyncio.queues import Queue
from collections.abc import Mapping

import websockets

# receive same SESSION_ID as browser
SESSION_ID = "secret-session-id"  # same id used by browser


def append_to_file(filename: str, content: str):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n")


def append_to_file_queue(filename: str, queue: Queue[str]):
    async def _append():
        while True:
            content = await queue.get()
            if content is None:  # signal to stop
                break
            append_to_file(filename, content)

    return _append()


async def consumer():
    file_write_queue: Queue[str] = Queue()
    asyncio.create_task(
        append_to_file_queue("following_users_data.txt", file_write_queue)
    )
    async with websockets.connect("ws://localhost:8765") as ws:
        # handshake
        hello = {"type": "hello", "role": "consumer", "session": SESSION_ID}
        await ws.send(json.dumps(hello))

        likers_data: Mapping[str, str] = {}
        command_queue: Queue[Mapping[str, str | list[str] | float] | None] = Queue()

        scrape_following_users_command = {
            "command": "sniff",
            "operation": "getAll",
            "selector": 'div[role="dialog"] a[role="link"]:nth-child(1)',
            "attribute": ["innerText", "href"],
        }

        scroll_down_command = {
            "command": "sniff",
            "operation": "scrollDown",
            "selector": "body > div.x1n2onr6.xzkaem6 > div:nth-child(2) > div > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div > div.x7r02ix.x15fl9t6.x1yw9sn2.x1evh3fb.x4giqqa.xb88tzc.xw2csxc.x1odjw0f.x5fp0pe > div > div > div.x6nl9eh.x1a5l9x9.x7vuprf.x1mg3h75.x1lliihq.x1iyjqo2.xs83m0k.xz65tgg.x1rife3k.x1n2onr6",
            "selectIndex": 0,  # select index 0, when viewing some post from feed. 1: when viewing from home page.
            "attribute": "",
            "amount": 1000,
        }

        async def listen():
            print("[Consumer] Started listening for messages...")
            retry = 0
            prev_likers_counts = 0
            async for msg in ws:
                # print("[Consumer] Received HTML:", msg)
                result = json.loads(msg)
                if result.get("messageType") == "sniffingResult" and (
                    data := result.get("data")
                ):
                    likers = data.get("innerText", [])
                    hrefs = data.get("href", [])
                    for liker, href in zip(likers, hrefs):
                        if liker not in likers_data:
                            likers_data[liker] = href
                            # store each liker to file immediately
                            await file_write_queue.put(f"{liker} - {href}")
                            print(f"[Consumer] {liker} - {href}")
                            # print(f"[Consumer] New liker found: {liker} - {href}")

                    # if prev_likers_counts == len(likers_data):
                    #     if retry < 3:  # retry a few times before giving up
                    #         print(
                    #             "[Consumer] No new likers found in this iteration. Retrying..."
                    #         )
                    #         await asyncio.sleep(5.0)  # wait before retrying
                    #         await command_queue.put(scroll_down_command)
                    #         retry += 1
                    #         continue
                    #     print(
                    #         "[Consumer] No new likers found in this iteration. Stopping further scrolls."
                    #     )
                    #     await ws.close()
                    #     await command_queue.put(None)  # signal to stop sending commands
                    #     return
                    prev_likers_counts = len(likers_data)
                    print(
                        f"[Consumer] Total unique likers collected: {len(likers_data)}"
                    )
                    # add scroll down command to queue, and scrape likers again; if no new likers found after several iterations, we can stop
                    await command_queue.put(scroll_down_command)
                    await command_queue.put(scrape_following_users_command)

                    print("[Consumer] Enqueued scroll down and scrape likers commands.")

        async def send_commands():
            command_queue.put_nowait(scrape_following_users_command)
            while next_cmd := await command_queue.get():
                if not next_cmd:
                    break
                await ws.send(json.dumps(next_cmd))

                if next_cmd["operation"] == "scrollDown":
                    await asyncio.sleep(2.0)  # wait between commands

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        await asyncio.gather(listen(), send_commands())

        return likers_data


try:
    likers_data = asyncio.run(consumer())
    print(f"Total unique likers collected: {len(likers_data)}")
    pprint.pprint(likers_data)
except KeyboardInterrupt:
    print("Consumer stopped by user.")
