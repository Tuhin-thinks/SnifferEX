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
            

            scroll_the_container = """
function isScrollable(el) {
      if (!el) return false;
      const style = getComputedStyle(el);
      const overflowY = style.overflowY;
      if (!/(auto|scroll)/.test(overflowY)) return false;
      return el.scrollHeight > el.clientHeight + 2;
    }

    function getScrollContainer(startFrom) {
      let el = startFrom || document.activeElement || document.body;
      while (el && el !== document.documentElement) {
        if (isScrollable(el)) return el;
        el = el.parentElement;
      }
      return document.scrollingElement || document.documentElement || document.body;
    }

    const container = getScrollContainer();
    container.scrollBy(0, 300);  // scroll down by 300 pixels
  }
"""
            selector_get_username = {
                "command": "sniff",
                "operation": "getAll",
                "selector": "div[data-testid=User-Name] a>div span>span",
                "attribute": ["innerText"],
            }

            scroll_command = {
                "command": "sniff",
                "operation": "scrollDown",
                "selector": "",
                "attribute": "",
                "amount": 300,
            }

            cmds = [
                # selector_get_username,
                scroll_command,
            ] * 10
            command_iterator = iter(cmds)
            while next_cmd := next(command_iterator, None):
                cmd = next_cmd
                await asyncio.sleep(2.0)  # wait between commands
                await ws.send(json.dumps(cmd))

            # completed sending all commands, close the connection after a short delay
            await asyncio.sleep(0.5)
            await ws.close()

        await asyncio.gather(listen(), send_commands())


asyncio.run(consumer())
