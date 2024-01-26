import asyncio
import json
import threading
from queue import Queue

import websockets
from websockets.server import serve

QUEUE_MAX_SIZE = 5


def logger(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}...")
        return func(*args, **kwargs)

    return wrapper


def serializer(obj):
    if not isinstance(obj, dict):
        raise TypeError("Expected type dict, got {0}".format(type(obj)))
    return json.dumps(obj)


def parser(obj):
    if not isinstance(obj, str):
        raise TypeError("Expected type str, got {0}".format(type(obj)))
    return json.loads(obj)


class WebSocketServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.connections = set()  # set of all connected clients
        self.commands_queue = Queue(maxsize=QUEUE_MAX_SIZE)  # queue of commands to be sent to the browser extension
        self.response_queue = Queue(maxsize=QUEUE_MAX_SIZE)  # queue of responses from the browser extension
        self.connection_delay_time = {}

    def start_server(self, threaded=False):
        if threaded:
            threading.Thread(target=self.run_server).start()
        else:
            self.run_server()

    def run_server(self):
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(self._run_server())

    async def _run_server(self):
        # async with serve(self.commands_stream, self.host, self.port):
        #     await asyncio.Future()
        server = await serve(self.listener, self.host, self.port)
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        await server.wait_closed()

    async def listener(self, websocket):
        self.connections.add(websocket)

        print("New client connected, Waiting for hello message from client...")
        request = await websocket.recv()  # receive hello message from client
        print(f"\nReceived [server]: {parser(request)}")

        # send the commands one by one from the commands queue to the browser extension
        while True:
            try:
                command = self.commands_queue.get()

                print(f"Sending command: {command}")
                await websocket.send(serializer(command))
                print("Command sent...")

                # wait for the response from the browser extension
                response = await websocket.recv()
                print(f"Received [server]: {response}")

                # put the response into the response queue
                self.response_queue.put(parser(response), timeout=10)  # client should be doing get() on this queue

            except websockets.ConnectionClosedOK:
                print("Connection closed...")
                self.connections.remove(websocket)
                break

    # async def commands_stream(self, websocket):
    #     init_value = await websocket.recv()
    #     print(f"Init value: {init_value}")
    #
    #     _time_str = datetime.now().strftime("%H:%M:%S")
    #     await self.send_message(websocket, {"message": f"connected {_time_str}"})
    #     print('Sent message...')
    #
    # async def disconnect(self, websocket):
    #     if websocket in self.connections:
    #         await websocket.close(1000, "Server closed connection")
    #         print(f"Closed connection...{websocket.remote_address}")
    #         self.connections.remove(websocket)
    #
    # async def send_message(self, connection: Optional[WebSocketServerProtocol], message: Union[dict, str]):
    #     if isinstance(message, dict):
    #         message_str = serializer(message)
    #     elif isinstance(message, str):
    #         message_str = message
    #     else:
    #         raise TypeError("Expected type dict or str, got {0}".format(type(message)))
    #
    #     if not connection:
    #         print("Sending message to all clients...\n"
    #               f"{list(map(lambda x: x.remote_address, self.connections))}")
    #         websockets.broadcast(self.connections, message_str)
    #         print("Done...")
    #     else:
    #         await connection.send(message_str)


# async def main():
#     server = WebSocketServer("localhost", 8765)
#     server_task = asyncio.create_task(server.start_server())
#     server_task.add_done_callback(lambda x: print("Server closed..."))
#     await server_task

#
# if __name__ == '__main__':
#     asyncio.run(main())
