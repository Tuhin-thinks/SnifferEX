import asyncio
import contextlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

from connection_handler import Connection

KEEPALIVE_INTERVAL_SECONDS = 20
BROWSER_HEARTBEAT_TIMEOUT_SECONDS = 75


@dataclass(slots=True)
class SessionState:
    browsers: dict[str, Connection] = field(default_factory=dict)
    consumers: set[Connection] = field(default_factory=set)
    last_active_tab_id: str | None = None


class SessionRouter:
    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def register(self, conn: Connection, role: str, session: str, tab_id: str | None):
        async with self._lock:
            conn.role = role
            conn.session = session
            conn.tab_id = tab_id
            conn.last_seen_at = time.time()

            state = self._sessions.setdefault(session, SessionState())

            if role == "browser":
                if not tab_id:
                    raise ValueError("Browser hello must include tabId")

                old_conn = state.browsers.get(tab_id)
                if old_conn and old_conn is not conn:
                    with contextlib.suppress(Exception):
                        await old_conn.websocket.close(code=4000, reason="superseded-by-new-tab-connection")

                state.browsers[tab_id] = conn
                state.last_active_tab_id = tab_id
                print(f"[+] browser {conn.id} session={session} tabId={tab_id}")
                return

            if role == "consumer":
                state.consumers.add(conn)
                print(f"[+] consumer {conn.id} session={session}")
                return

            raise ValueError(f"Unsupported role: {role}")

    async def unregister(self, conn: Connection):
        async with self._lock:
            session = conn.session
            if not session:
                return

            state = self._sessions.get(session)
            if not state:
                return

            if conn.role == "browser" and conn.tab_id:
                state.browsers.pop(conn.tab_id, None)
                if state.last_active_tab_id == conn.tab_id:
                    state.last_active_tab_id = next(iter(state.browsers.keys()), None)
            elif conn.role == "consumer":
                state.consumers.discard(conn)

            if not state.browsers and not state.consumers:
                self._sessions.pop(session, None)

            print(
                f"[-] {conn.role} {conn.id} session={session}"
                + (f" tabId={conn.tab_id}" if getattr(conn, "tab_id", None) else "")
            )

    async def mark_alive(self, conn: Connection):
        async with self._lock:
            conn.last_seen_at = time.time()
            if conn.role == "browser" and conn.session and conn.tab_id:
                state = self._sessions.get(conn.session)
                if state:
                    state.last_active_tab_id = conn.tab_id

    async def consumers_for(self, session: str) -> list[Connection]:
        async with self._lock:
            state = self._sessions.get(session)
            return list(state.consumers) if state else []

    async def target_browser(self, session: str, target_tab_id: str | None) -> Connection | None:
        async with self._lock:
            state = self._sessions.get(session)
            if not state or not state.browsers:
                return None

            if target_tab_id:
                return state.browsers.get(target_tab_id)

            if state.last_active_tab_id:
                selected = state.browsers.get(state.last_active_tab_id)
                if selected:
                    return selected

            return next(iter(state.browsers.values()))

    async def stale_browsers(self, now_ts: float, timeout_seconds: float) -> list[Connection]:
        stale: list[Connection] = []
        async with self._lock:
            for state in self._sessions.values():
                for browser in state.browsers.values():
                    if now_ts - getattr(browser, "last_seen_at", now_ts) > timeout_seconds:
                        stale.append(browser)
        return stale

    async def all_connections(self) -> list[Connection]:
        async with self._lock:
            all_conns: list[Connection] = []
            for state in self._sessions.values():
                all_conns.extend(state.browsers.values())
                all_conns.extend(state.consumers)
            return all_conns


router = SessionRouter()


def serialize_raw(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    if isinstance(raw, bytearray):
        return bytes(raw).decode("utf-8", errors="replace")
    if isinstance(raw, memoryview):
        return raw.tobytes().decode("utf-8", errors="replace")
    return str(raw)


def try_json(raw: Any):
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def to_json(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"))


def is_heartbeat(payload: dict | None) -> bool:
    if not payload:
        return False
    return payload.get("messageType") == "heartbeat" or payload.get("command") == "heartbeat"


async def enqueue(conn: Connection, payload: str):
    try:
        conn.outgoing.put_nowait(payload)
    except asyncio.QueueFull:
        print(f"[!] Dropping message for role={conn.role} session={conn.session} id={conn.id}")


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


async def process_browser_message(conn: Connection, raw: Any):
    payload = try_json(raw)
    await router.mark_alive(conn)

    if is_heartbeat(payload):
        await enqueue(
            conn,
            to_json(
                {
                    "messageType": "heartbeat",
                    "tabId": conn.tab_id,
                    "timestamp": int(time.time() * 1000),
                    "source": "server",
                }
            ),
        )
        return

    outbound = payload if isinstance(payload, dict) else None
    if outbound is not None:
        outbound.setdefault("tabId", conn.tab_id)
        serialized = to_json(outbound)
    else:
        serialized = serialize_raw(raw)

    if conn.session is None:
        return

    peers = await router.consumers_for(conn.session)
    if not peers:
        print(f"[!] No consumer connected for session={conn.session}")
        return

    for peer in peers:
        await enqueue(peer, serialized)


async def process_consumer_message(conn: Connection, raw: Any):
    payload = try_json(raw)
    await router.mark_alive(conn)

    if is_heartbeat(payload):
        await enqueue(
            conn,
            to_json({"messageType": "heartbeat", "timestamp": int(time.time() * 1000), "source": "server"}),
        )
        return

    target_tab_id = None
    if isinstance(payload, dict):
        candidate = payload.get("tabId") or payload.get("targetTabId")
        if candidate is not None:
            target_tab_id = str(candidate)

    if conn.session is None:
        return

    peer = await router.target_browser(conn.session, target_tab_id)
    if not peer:
        print(f"[!] No browser available for session={conn.session} target_tab={target_tab_id}")
        return

    if isinstance(payload, dict):
        payload.setdefault("tabId", peer.tab_id)
        payload.setdefault("targetTabId", peer.tab_id)
        await enqueue(peer, to_json(payload))
        return

    serialized = serialize_raw(raw)
    await enqueue(peer, serialized)


async def reader(conn: Connection):
    hello_raw = await conn.websocket.recv()
    hello = try_json(hello_raw)

    if not isinstance(hello, dict):
        print("[!] Invalid hello message: expected JSON object")
        await conn.websocket.close(code=4001, reason="invalid-hello")
        return

    role = hello.get("role")
    session = hello.get("session")
    tab_id = hello.get("tabId")

    if role is None or session is None:
        print("[!] Invalid hello message, missing role or session")
        print(f"[!] Received: {hello}")
        await conn.websocket.close(code=4001, reason="missing-role-or-session")
        return

    role = str(role)
    session = str(session)
    tab_id = str(tab_id) if tab_id is not None else None

    try:
        await router.register(conn, role, session, tab_id)
    except ValueError as exc:
        print(f"[!] Registration failed: {exc}")
        await conn.websocket.close(code=4001, reason=str(exc))
        return

    async for raw in conn.websocket:
        if conn.role == "browser":
            await process_browser_message(conn, raw)
        elif conn.role == "consumer":
            await process_consumer_message(conn, raw)


async def keepalive_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        await asyncio.sleep(KEEPALIVE_INTERVAL_SECONDS)
        now_ms = int(time.time() * 1000)

        for conn in await router.all_connections():
            if conn.role == "browser":
                payload = {"messageType": "heartbeat", "tabId": conn.tab_id, "timestamp": now_ms, "source": "server"}
            else:
                payload = {"messageType": "heartbeat", "timestamp": now_ms, "source": "server"}
            await enqueue(conn, to_json(payload))

        stale = await router.stale_browsers(time.time(), BROWSER_HEARTBEAT_TIMEOUT_SECONDS)
        for browser in stale:
            print(
                f"[!] Closing stale browser connection session={browser.session} tabId={browser.tab_id}"
            )
            with contextlib.suppress(Exception):
                await browser.websocket.close(code=4002, reason="heartbeat-timeout")


async def handle_connection(websocket: ServerConnection):
    conn = Connection(websocket)
    writer_task = asyncio.create_task(writer(conn))
    reader_task = asyncio.create_task(reader(conn))

    try:
        await reader_task
    finally:
        writer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writer_task
        await router.unregister(conn)


async def main():
    stop_event = asyncio.Event()
    keepalive_task = asyncio.create_task(keepalive_loop(stop_event))

    try:
        async with serve(
            handle_connection,
            "localhost",
            8765,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as server:
            print("[i] WS server started on ws://localhost:8765")
            await server.serve_forever()
    finally:
        stop_event.set()
        keepalive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keepalive_task


if __name__ == "__main__":
    asyncio.run(main())
