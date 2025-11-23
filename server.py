#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
import simpleaudio as sa
from typing import List
from time import time

logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to log
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

SHOW = [
    {"t": 0.0, "id": "79563461152192-14", "state": 0.0},
    {"t": 1.0, "id": "79563461152192-14", "state": 0.0},
    {"t": 1.2, "id": "79563461152192-14", "state": 1.0},
    {"t": 5, "id": "79563461152192-14", "state": 0.0},
    {"t": 8, "id": "79563461152192-14", "state": 1.0},
    # ...
]

SHOW = [
    {"t": i, "id": "79563461152192-14", "state": float(i%2)} for i in range(60)
]


class WebsocketServer:

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.connections: Dict[str, Any] = {}

    def parse_connect_message(self, message: str) -> List[str]:
        data = json.loads(message)
        if 'ids' not in data:
            raise KeyError("Message missing 'ids', ignoring.")
        ids = data['ids']

        # Raise error if duplicate IDs received from one websocket
        if len(ids) != len(set(ids)):
            raise KeyError("Duplicate id in 'ids', ignoring.")
        return data["ids"]

    async def handle_connect(self, websocket):
        logging.info("Received connection!")
        ids_for_this_ws = set()
        try:
            async for message in websocket:        # keeps the connection alive
                logging.info(f"Received message: {message}")
                ids = self.parse_connect_message(message)

                for _id in ids:
                    old = self.connections.get(_id)
                    if old and old is not websocket:
                        logging.warning(f"Duplicate ID {_id}; replacing old socket")
                        try:
                            await old.close()
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
            await self.send_state(id, state)

    async def send_state(self, id: str, state: float):
        ws = self.connections.get(id)
        if not ws:
            logging.warning(f"No connection for ID {id}, skipping")
            return
        msg = json.dumps({"id": id, "state": float(state)})
        try:
            await ws.send(msg)
            logging.info(f"Sent to {id}: {state}")
        except Exception as e:
            logging.warning(f"Error sending to {id}: {e}")

    async def play_show(self, wav_path: Path, cues: List):

        await asyncio.sleep(8)

        logging.info("Loading from wav")
        audio_file = sa.WaveObject.from_wave_file(str(wav_path))

        logging.info("Playing wav")
        play_obj = audio_file.play()
        logging.info("After")

        start = time()

        cues = sorted(cues, key=lambda x: x['t'])

        for cue in cues:
            t = cue['t']
            id = cue['id']
            state = cue['state']

            now = time() - start

            if t > now:
                await asyncio.sleep(t - now)

            now = time() - start
            await self.send_state(id, state)
            logging.info(f"{t}: {id} -> {state}\t\t({now})")

        # Optionally wait until audio finishes (in a thread, since wait_done is blocking)
        await asyncio.to_thread(play_obj.wait_done)
        logging.info("Done with song!")


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
    
    await asyncio.gather(server.serve(), server.console(), server.play_show(Path("./whitechristmas.wav"), SHOW))

if __name__ == "__main__":
    asyncio.run(main())

