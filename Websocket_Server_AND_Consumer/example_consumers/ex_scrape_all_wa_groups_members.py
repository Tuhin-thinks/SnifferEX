"""This example can scrape all user's phone numbers from all WhatsApp groups the user is part of. You have to keep the WhatsApp Web dashboard open."""

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

        members_data: set[str] = set()
        command_queue: Queue[Mapping[str, str | list[str] | float] | None] = Queue()

        users_phone_selector = {
            "command": "sniff",
            "operation": "getAll",
            "selector": "div._ak8j > div._ak8i > span._ajzr > span",
            "attribute": ["innerText"],
        }

        scroll_down_command = {
            "command": "sniff",
            "operation": "scrollDown",
            "selector": "div.copyable-area",
            "selectIndex": 1,
            "attribute": "",
            "amount": 1000,
        }

        async def listen():
            prev_members_counts = 0
            async for msg in ws:
                # print("[Consumer] Received HTML:", msg)
                result = json.loads(msg)
                if result.get("messageType") == "sniffingResult" and (
                    data := result.get("data")
                ):
                    phone_numbers = data.get("innerText", [])
                    for phone in phone_numbers:
                        if phone not in members_data:
                            # print(f"[Consumer] New member found: {phone}")
                            members_data.add(phone)

                    if prev_members_counts == len(members_data):
                        print(
                            "[Consumer] No new members found in this iteration. Stopping further scrolls."
                        )
                        await ws.close()
                        await command_queue.put(None)  # signal to stop sending commands
                        return
                    prev_members_counts = len(members_data)

        async def send_commands():
            await asyncio.sleep(2)  # wait for 2 seconds before starting
            await command_queue.put(users_phone_selector)
            while True:
                command = await command_queue.get()
                if command is None:
                    print("[Consumer] Stopping command sender.")
                    break
                await ws.send(json.dumps(command))
                await asyncio.sleep(2)  # wait for 2 seconds between commands
                if command == users_phone_selector:
                    await command_queue.put(scroll_down_command)
                elif command == scroll_down_command:
                    await command_queue.put(users_phone_selector)

        await asyncio.gather(listen(), send_commands())

        print(
            f"[Consumer] Scraping completed. {len(members_data)} unique members found."
        )
        return members_data


try:
    members_data = asyncio.run(consumer())
    print(f"[Consumer] Scraping completed. {len(members_data)} unique members found.")
    pprint.pprint(members_data)
except Exception as e:
    print(f"[Consumer] Error occurred: {e}")
