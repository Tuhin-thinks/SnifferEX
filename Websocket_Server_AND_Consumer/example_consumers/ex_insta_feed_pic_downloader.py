# consumer_client.py
import asyncio
import json
import pprint

import websockets

# receive same SESSION_ID as browser
SESSION_ID = "secret-session-id"  # same id used by browser
unique_links = set()


async def consumer():
    async with websockets.connect("ws://localhost:8765") as ws:
        # handshake
        hello = {"type": "hello", "role": "consumer", "session": SESSION_ID}
        scroll_command = {
            "command": "sniff",
            "operation": "scrollDown",
            "selector": "",
            "attribute": "",
            "amount": 1000,
        }

        get_images_command = {
            "command": "sniff",
            "operation": "getAll",
            "selector": "div>img",
            "attribute": ["src", "alt"],
        }
        await ws.send(json.dumps(hello))
        command_queue = asyncio.Queue()

        async def listen():
            async for msg in ws:
                # print("[Consumer] Received HTML:", msg)
                # pprint.pprint(json.loads(msg))
                if parsed_response := json.loads(msg):
                    if parsed_response.get("messageType") == "sniffingResult" and (
                        data := parsed_response.get("data")
                    ):
                        pprint.pprint(parsed_response)
                        urls = set(data["src"])
                        prev_count = len(unique_links)
                        unique_links.update(urls)
                        if len(unique_links) > prev_count:
                            print(
                                f"[Consumer] Collected {len(unique_links)} unique image links so far."
                            )
                            await command_queue.put(get_images_command)
                            await command_queue.put(scroll_command)
                        # enqueue next command if available
                        else:
                            await command_queue.put(scroll_command)
                            await command_queue.put(get_images_command)
                        print(
                            f"[Consumer] Total unique image links collected: {len(unique_links)}"
                        )

        async def send_commands():
            command_queue.put_nowait(get_images_command)
            command_queue.put_nowait(scroll_command)

            while next_cmd := await command_queue.get():
                cmd = next_cmd
                await ws.send(json.dumps(cmd))

                if cmd["operation"] == "scrollDown":
                    await asyncio.sleep(2.0)  # wait between commands

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        try:
            await asyncio.gather(listen(), send_commands())
        except (Exception, KeyboardInterrupt) as e:
            print(f"Error occurred: {e}")
            # store all gathered links before exiting
            print(f"[Consumer] Final unique image links collected: {len(unique_links)}")


try:
    asyncio.run(consumer())
except KeyboardInterrupt:
    print("Consumer client stopped by user.")
    with open("downloaded_image_links.json", "w", encoding="utf-8") as f:
        for link in unique_links:
            f.write(link + "\n")
