import queue
from typing import List, Dict, Union

"""
file: wsConnectionHandler.py
This file is to handle the websocket connection between the Python automator script and the websocket server.
"""

from ws_server import WebSocketServer


class WsConnectionHandler:
    instance = None

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance') or not cls.instance:
            cls.instance = super(WsConnectionHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.ws_server: Union[WebSocketServer, None] = None

    def connect_server(self):
        """
        Connect to the websocket server.
        """
        ws_server = WebSocketServer(self.host, self.port)
        ws_server.start_server(threaded=True)

        self.ws_server = ws_server

    def ask_browser(self, commands_list: List[Dict]):
        """
        Send commands to the browser extension.
        """
        for command in commands_list:
            command.setdefault('command', 'sniff')
            try:
                self.ws_server.commands_queue.put(command)
            except queue.Full:
                raise RuntimeError("Queue is full. Please try again later.")

    def get_responses(self, n_response=1):
        """
        Get response from the browser extension.
        """
        print("Waiting for response...")
        while n_response > 0:
            try:
                response = self.ws_server.response_queue.get(timeout=10)
                n_response -= 1
                print(f">> response: {response}\n"
                      f"Remaining: {n_response}\n")
                return [response]
            except queue.Empty:
                print("No response received from browser extension. Please try again later.")
                break

        return []
