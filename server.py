#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
import json
from typing import List, Dict, Any
import logging

logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to log
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class WebsocketServer:

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.connections: Dict[str, Any] = {}

    def parse_connect_message(self, message: str) -> List[str]:
        data = json.loads(message)
        if 'ids' not in data:
            raise KeyError("Message missing 'ids', ignoring.")
        return data["ids"]

    async def handle_connect(self, websocket):
        logging.info("Received connection!")
        ids_for_this_ws = set()
        try:
            async for message in websocket:        # keeps the connection alive
                logging.info(f"Received message: {message}")
                try:
                    ids = self.parse_connect_message(message)
                except Exception as e:
                    logging.warning(f"Bad message: {e}")
                    continue                        # don't exit; keep socket alive

                for _id in ids:
                    old = self.connections.get(_id)
                    if old and old is not websocket:
                        logging.warning(f"Duplicate ID {_id}; replacing old socket")
                        try:
                            await old.close()       # or decide to reject the new one
                        except Exception:
                            pass
                    self.connections[_id] = websocket
                    logging.info(f"Added connection for ID: {_id}")
                    ids_for_this_ws.add(_id)

        except Exception as e:
            logging.info(f"Connection error: {e}")
        finally:
            # remove any IDs tied to this websocket
            for _id in list(ids_for_this_ws):
                self.connections.pop(_id, None)

    async def console(self):
        while True:
            cmd = (await asyncio.to_thread(input, ">> "))
            args = cmd.split(',')
            if len(args) != 2:
                continue
            id, state = args
            if id in self.connections:
                await self.connections[id].send(json.dumps({"id": id, "state": float(state)}))
                logging.info(f"Send ID {id} -> {state}")

    async def serve(self):
        logging.info(f"Starting websocket server: ws://{self.host}:{self.port}")
        async with serve(self.handle_connect, self.host, self.port) as server:
            await server.serve_forever()

async def main():
    """
    Starts the WebSocket server.
    """
    host = "192.168.1.210"
    port = 8765
    server = WebsocketServer(host, port)
    
    await asyncio.gather(server.serve(), server.console())

if __name__ == "__main__":
    asyncio.run(main())

