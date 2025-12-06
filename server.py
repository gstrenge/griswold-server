#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
import simpleaudio as sa
from collections import OrderedDict
from queue import Queue
from typing import List
import datetime
from dataclasses import dataclass
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

@dataclass
class DailySchedule:
    start_time: datetime.time
    end_time: datetime.time

@dataclass
class LightCue:
    t: float
    id: str
    state: float

@dataclass
class LightShow:
    song_name: str
    music_file: Path
    light_cues: List[LightCue]

WHITE_CHRISTMAS = [
    # Intialize start to on
    {"t": 0.0, "id": "1A", "state": 0.0},
    {"t": 0.0, "id": "1B", "state": 0.0},
    {"t": 0.0, "id": "2A", "state": 0.0},
    {"t": 0.0, "id": "2B", "state": 0.0},
    {"t": 0.0, "id": "3A", "state": 0.0},
    {"t": 0.0, "id": "3B", "state": 0.0},
    {"t": 0.0, "id": "4A", "state": 0.0},
    {"t": 0.0, "id": "4B", "state": 0.0},
    {"t": 0.0, "id": "5A", "state": 0.0},
    {"t": 0.0, "id": "5B", "state": 0.0},
    {"t": 0.0, "id": "6A", "state": 0.0},
    {"t": 0.0, "id": "6B", "state": 0.0},

    # Initial 4 notes (turn things off)
    {"t": 2.6, "id": "1A", "state": 1.0},
    {"t": 2.6, "id": "1B", "state": 1.0},
    {"t": 2.6, "id": "6A", "state": 1.0},
    {"t": 2.6, "id": "6B", "state": 1.0},

    {"t": 3.75, "id": "2A", "state": 1.0},
    {"t": 3.75, "id": "2B", "state": 1.0},
    {"t": 3.75, "id": "5A", "state": 1.0},
    {"t": 3.75, "id": "5B", "state": 1.0},

    {"t": 5.12, "id": "3A", "state": 1.0},
    {"t": 5.12, "id": "4B", "state": 1.0},

    {"t": 6.21, "id": "3B", "state": 1.0},
    {"t": 6.21, "id": "4A", "state": 1.0},

    # Second 4 notes, turn things on
    {"t": 7.55, "id": "1B", "state": 0.0},
    {"t": 7.55, "id": "1A", "state": 0.0},
    {"t": 7.55, "id": "6A", "state": 0.0},
    {"t": 7.55, "id": "6B", "state": 0.0},

    {"t": 8.78, "id": "2A", "state": 0.0},
    {"t": 8.78, "id": "5B", "state": 0.0},

    {"t": 10.05, "id": "2B", "state": 0.0},
    {"t": 10.05, "id": "5A", "state": 0.0},

    {"t": 10.54, "id": "3A", "state": 0.0},
    {"t": 10.54, "id": "4B", "state": 0.0},

    {"t": 11.20, "id": "3B", "state": 0.0},
    {"t": 11.20, "id": "4A", "state": 0.0},
]

WHITE_CHRISTMAS = [
    # Intialize start to on
    {"t": 0.0, "id": "1A", "state": 0.0},
    {"t": 0.0, "id": "1B", "state": 0.0},
    {"t": 0.0, "id": "2A", "state": 0.0},
    {"t": 0.0, "id": "2B", "state": 0.0},
    {"t": 0.0, "id": "3A", "state": 0.0},
    {"t": 0.0, "id": "3B", "state": 0.0},
    {"t": 0.0, "id": "4A", "state": 1.0},
    {"t": 0.0, "id": "4B", "state": 1.0},
    {"t": 0.0, "id": "6A", "state": 0.0},
    {"t": 0.0, "id": "6B", "state": 0.0},

    # Initial 4 notes (turn things off)
    {"t": 2.6, "id": "1B", "state": 1.0},
    {"t": 2.6, "id": "1A", "state": 1.0},
    {"t": 2.6, "id": "6B", "state": 1.0},
    {"t": 2.6, "id": "6A", "state": 1.0},

    {"t": 3.75, "id": "2B", "state": 1.0},
    # {"t": 3.75, "id": "4A", "state": 1.0},

    {"t": 5.12, "id": "2A", "state": 1.0},
    # {"t": 5.12, "id": "4B", "state": 1.0},

    {"t": 6.21, "id": "3B", "state": 1.0},
    {"t": 5.21, "id": "3A", "state": 1.0},

    # Second 4 notes, turn things on
    {"t": 7.55, "id": "1B", "state": 0.0},
    {"t": 7.55, "id": "6A", "state": 0.0},

    {"t": 8.78, "id": "1A", "state": 0.0},
    {"t": 8.78, "id": "6B", "state": 0.0},

    {"t": 10.05, "id": "2B", "state": 0.0},
    # {"t": 10.05, "id": "4A", "state": 0.0},

    {"t": 10.54, "id": "2A", "state": 0.0},
    # {"t": 10.54, "id": "4B", "state": 0.0},

    {"t": 11.20, "id": "3B", "state": 0.0},
    {"t": 11.20, "id": "3A", "state": 0.0},
    
    {"t": 11.20, "id": "SNOWMACHINE_1", "state": 1.0},
    {"t": 11.20, "id": "4A", "state": 0.0},
    {"t": 11.20, "id": "4B", "state": 0.0},
    {"t": 28.20, "id": "SNOWMACHINE_1", "state": 0.0},
    

]

SHOW = [
    {"t": i, "id": "79563461152192-14", "state": float(i%2)} for i in range(60)
]

class WebsocketServer:

    def __init__(self, host, port, id_mapping: Dict[str, str], playlist: List[LightShow], schedule: DailySchedule):
        self.host = host
        self.port = port
        self.id_mapping = id_mapping
        self.reverse_id_mapping = {value: key for key, value in id_mapping.items()}
        
        # Represents the schedule of when to start playing and when to stop playing
        self.schedule = schedule
        
        # Represents the playlist being repeated
        self.playlist: List[LightShow] = playlist
        # Represents the playlist queue
        self.queue: Queue[LightShow] = Queue()
        # Represents the actively requested songs that have priority
        self.request_queue: Queue[LightCue] = Queue()

        self.connections: Dict[str, Any] = {}
        
    def skip(self):
        pass
    
    def pause(self):
        pass
    
    def play(self):
        pass

    def parse_connect_message(self, message: str) -> List[str]:
        data = json.loads(message)
        if 'ids' not in data:
            raise KeyError("Message missing 'ids', ignoring.")
        ids = data['ids']

        # Raise error if duplicate IDs received from one websocket
        if len(ids) != len(set(ids)):
            raise KeyError("Duplicate id in 'ids', ignoring.")
        return data["ids"]
    
    def preprocess_show(self, cues) -> OrderedDict[List[Dict[str,str]]]:
        """Combines same-time events into one event."""
        sorted_cue = sorted(cues, key=lambda x: x['t'])
        ordered_dict_cue = OrderedDict() # I believe dictionary order is preserved

        for cue in cues:
            t = cue['t']
            if t not in ordered_dict_cue:
                ordered_dict_cue[t] = []
            # Add to that cue
            ordered_dict_cue[t].append({"id": cue["id"], "state": cue["state"]})

        return ordered_dict_cue

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
            cmd_type = args[0]

            # Connections
            if cmd_type == "c":
                logging.info("Connections:")
                logging.info("\n".join(self.connections.keys()))
                
            elif cmd_type == "q":
                logging.info("Adding to queue")
                self.request_queue.put(LightShow("test", Path("test.mp3"), []))
                
            elif cmd_type == "snow":
                logging.info("Turning on snow machine")
                snowmachine_id = self.reverse_id_mapping.get("SNOWMACHINE_1")
                spotlight1_id = self.reverse_id_mapping.get("4A")
                spotlight2_id = self.reverse_id_mapping.get("4B")
                
                await asyncio.gather(
                    self.send_state(snowmachine_id, 1.0),
                    self.send_state(spotlight1_id, 0.0),
                    self.send_state(spotlight2_id, 0.0),
                )
                
            elif cmd_type == "nosnow":
                logging.info("Turning off snow machine")
                snowmachine_id = self.reverse_id_mapping.get("SNOWMACHINE_1")
                spotlight1_id = self.reverse_id_mapping.get("4A")
                spotlight2_id = self.reverse_id_mapping.get("4B")
                
                await asyncio.gather(
                    self.send_state(snowmachine_id, 0.0),
                    self.send_state(spotlight1_id, 1.0),
                    self.send_state(spotlight2_id, 1.0),
                )

            # Set
            elif cmd_type == "sr":
                if len(args) != 3:
                    continue
                id, state = args[1:]
                await self.send_state(id, state)

            elif cmd_type == "s":
                if len(args) != 3:
                    continue
                id, state = args[1:]

                mapped_id = self.reverse_id_mapping.get(id)
                if mapped_id is None:
                    logging.warn("Invalid ID")
                    continue

                await self.send_state(mapped_id, state)

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
            
    async def run(self):
        try:
            logging.info("Beginning queue")
            while True:
                now = datetime.datetime.now().time()
                # If we are out of the scheduled time
                # if now < self.schedule.start_time or now > self.schedule.end_time:
                #     logging.info("Outside of schedule")
                #     await asyncio.sleep(60)
                #     continue
                
                # We are inside the current scheduled time
                logging.info("Inside of schedule, playing next")

                # Check queue first
                if not self.request_queue.empty():
                    logging.info("Playing from request queue")
                    song = self.request_queue.get()
                else:
                    logging.info("Playing from playlist queue")
                    if self.queue.empty():
                        logging.info("Refilling queue")
                        # If the queue is empty, refill it
                        for show in self.playlist:
                            self.queue.put(show)
                    song = self.queue.get()
                await self.play_show(song)
        except Exception as e:
            logging.error(e)
            logging.error(e.with_traceback())
    def get_queue(self):
        """Gets the current view only queue that reflects the order of which songs are played next"""
        return list(self.request_queue.queue) + list(self.queue.queue)
    
    async def play_show(self, show: LightShow):
        logging.info(f"Playing {show.song_name}")
        await asyncio.sleep(10)
        logging.info(f"Finished {show.song_name}")

    async def play_show_old(self, wav_path: Path, cues: List):

        await asyncio.sleep(10)

        logging.info("Loading from wav")
        audio_file = sa.WaveObject.from_wave_file(str(wav_path))

        logging.info("Playing wav")
        play_obj = audio_file.play()
        logging.info("After")

        start = time()

        cues = self.preprocess_show(cues)
        logging.info("Preprocessed cues")

        for timestamp in cues:
            try:

                now = time() - start

                if timestamp > now:
                    logging.info(f"Waiting for {timestamp}, it is currently {now}")
                    await asyncio.sleep(timestamp - now)

                now = time() - start

                cue_data = cues[timestamp]
                futures = []
                for event in cue_data:
                    id = event['id']
                    state = event['state']
                    id = self.reverse_id_mapping[id]
                    logging.info(f"{timestamp}: {id} -> {state}\t\t({now})")
                    futures.append(self.send_state(id, state))
                await asyncio.gather(*futures)

            except Exception as e:
                logging.error(e)
                logging.error(e.with_traceback())
                return

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

    id_mapping_path = Path(__file__).parent / "id_mapping.json"
    with open(id_mapping_path, "r") as id_mapping_file:
        id_mapping = json.load(id_mapping_file)
        
    white_christmas1 = LightShow("White Christmas 1", "./short.wav", [])
    white_christmas2 = LightShow("White Christmas 2", "./short.wav", [])
    white_christmas3 = LightShow("White Christmas 3", "./short.wav", [])
    white_christmas_req = LightShow("White Christmas Requested", "./short.wav", [])
    
    playlist = [white_christmas1, white_christmas2, white_christmas3]
    
    # Make a schedule with datetime that just represents time of day with no dates
    
    schedule = DailySchedule(datetime.time(17, 0), datetime.time(23, 0))

    host = "192.168.1.10"
    port = 8765
    server = WebsocketServer(host, port, id_mapping, playlist, schedule)
    
    await asyncio.gather(server.serve(), server.console(), server.play_show_old(Path("./whitechristmas.wav"), WHITE_CHRISTMAS))
    # await asyncio.gather(server.console(), server.run())
    # await asyncio.gather(server.serve(), server.console(), server.run())
    # await asyncio.gather(server.serve(), server.console())

if __name__ == "__main__":
    asyncio.run(main())

