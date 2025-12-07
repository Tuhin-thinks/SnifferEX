import asyncio
import uuid

from websockets import ServerConnection


class Connection:
    def __init__(self, websocket: ServerConnection):
        self.id = str(uuid.uuid4())
        self.websocket: ServerConnection = websocket
        self.role: None | str = None  # "browser" or "consumer"
        self.session: None | str = None  # shared session id
        self.outgoing: asyncio.Queue[str | bytes] = asyncio.Queue(maxsize=100)


class ConnectionManager:
    def __init__(self):
        self.browsers = {}  # session -> Connection
        self.consumers = {}  # session -> Connection
        self._lock = asyncio.Lock()

    async def register(self, conn: Connection, role: str, session: str):
        async with self._lock:
            conn.role = role
            conn.session = session
            if role == "browser":
                self.browsers[session] = conn
            elif role == "consumer":
                self.consumers[session] = conn
            print(f"[+] {role} {conn.id} for session={session}")

    async def unregister(self, conn: Connection):
        async with self._lock:
            if conn.role == "browser" and conn.session in self.browsers:
                self.browsers.pop(conn.session, None)
            elif conn.role == "consumer" and conn.session in self.consumers:
                self.consumers.pop(conn.session, None)
            print(f"[-] {conn.role} {conn.id} for session={conn.session}")

    async def get_peer(self, conn: Connection):
        """Return the other side (browser<->consumer) for this connection."""
        if conn.role == "browser":
            return self.consumers.get(conn.session)
        elif conn.role == "consumer":
            return self.browsers.get(conn.session)
        return None
