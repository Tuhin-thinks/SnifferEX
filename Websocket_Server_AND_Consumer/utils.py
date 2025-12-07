from websockets import ServerConnection


class Connection:
    def __init__(self, ws: ServerConnection, conn_id: str, client_id: str) -> None:
        self.ws = ws
        self.conn_id = conn_id
        self.client_id = client_id

    def __repr__(self) -> str:
        return f"Connection(conn_id={self.conn_id}, client_id={self.client_id})"
