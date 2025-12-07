import asyncio
import contextlib
import json

from websockets.asyncio.server import serve

from connection_handler import Connection, ConnectionManager

manager = ConnectionManager()


async def writer(conn: Connection):
    try:
        while True:
            msg = await conn.outgoing.get()
            try:
                await conn.websocket.send(msg)
            except Exception:
                break
            finally:
                conn.outgoing.task_done()
    finally:
        with contextlib.suppress(Exception):
            await conn.websocket.close()


async def reader(conn: Connection):
    # first message must be a hello with role+session
    hello_raw = await conn.websocket.recv()
    hello = json.loads(hello_raw)

    role = hello["role"]
    session = hello["session"]

    await manager.register(conn, role, session)

    # now handle normal messages
    async for raw in conn.websocket:
        peer = await manager.get_peer(conn)
        if not peer:
            # peer not connected yet – you can buffer or ignore
            print(f"[!] No peer for session={conn.session}, role={conn.role}")
            continue

        # For now we just forward raw message as-is
        try:
            peer.outgoing.put_nowait(raw)
        except asyncio.QueueFull:
            print(f"[!] Dropping message for peer in session={conn.session}")


async def handle_connection(websocket):
    conn = Connection(websocket)
    writer_task = asyncio.create_task(writer(conn))
    reader_task = asyncio.create_task(reader(conn))

    try:
        await reader_task
    finally:
        writer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writer_task
        await manager.unregister(conn)


async def main():
    async with serve(handle_connection, "localhost", 8765):
        print("[i] WS server started on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
