#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
import pygame
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

class WebsocketServer:

    def __init__(self, host, port, id_mapping: Dict[str, str], playlist_path: str, schedule: DailySchedule):
        self.host = host
        self.port = port
        self.id_mapping = id_mapping
        self.reverse_id_mapping = {value: key for key, value in id_mapping.items()}

        pygame.mixer.init()
        
        # Represents the schedule of when to start playing and when to stop playing
        self.schedule = schedule
        
        # Represents the playlist being repeated
        self.playlist_path = playlist_path
        self.playlist: List[LightShow] = []

        if not self.load_playlist():
            logging.error("Failed to load playlist!")
            raise Exception("Failed to load playlist!")
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
                await asyncio.gather(
                    self.send_state("SNOWMACHINE_1", 1.0),
                    self.send_state("4A", 0.0),
                    self.send_state("4B", 0.0),
                )
                
            elif cmd_type == "nosnow":
                logging.info("Turning off snow machine")
                await asyncio.gather(
                    self.send_state("SNOWMACHINE_1", 0.0),
                    self.send_state("4A", 1.0),
                    self.send_state("4B", 1.0),
                )

            # Set
            elif cmd_type == "sr":
                if len(args) != 3:
                    continue
                id, state = args[1:]
                await self._send_state(id, state)

            elif cmd_type == "s":
                if len(args) != 3:
                    continue
                id, state = args[1:]
                await self.send_state(id, state)

    async def _send_state(self, raw_id: str, state: float):
        ws = self.connections.get(raw_id)
        if not ws:
            logging.warning(f"No connection for ID {raw_id}, skipping")
            return
        msg = json.dumps({"id": raw_id, "state": 1.0 - float(state)})
        try:
            await ws.send(msg)
            logging.info(f"Sent to {raw_id}: {state}")
        except Exception as e:
            logging.warning(f"Error sending to {raw_id}: {e}")

    async def send_state(self, id: str, state: float):
        raw_id = self.reverse_id_mapping.get(id)
        if raw_id is None:
            logging.warning(f"ID {id} not found in mapping! Ignoring...")
            return
        await self._send_state(raw_id, state)
            
    async def run_forever(self):
        try:
            await self.run()
        except Exception as e:
            logging.error(e)
            logging.error(e.with_traceback())

    async def run(self):
        await asyncio.sleep(60)
        logging.info("Running server")
        while True:
            now = datetime.datetime.now().time()
            # If we are out of the scheduled time
            if now < self.schedule.start_time or now > self.schedule.end_time:
                logging.info("Outside of schedule")
                await asyncio.sleep(60)
                continue

            # Check queue first
            if not self.request_queue.empty():
                selected_queue_msg = "[Request]"
                show = self.request_queue.get()
            else:
                if self.queue.empty():
                    logging.info("Queue is empty, refreshing playlist.")
                    # If the queue is empty, refill it
                    self.load_playlist()
                    logging.info(f"Refilling queue with playlist: {[show.song_name for show in self.playlist]}")
                    for show in self.playlist:
                        self.queue.put(show)
                selected_queue_msg = "[Playlist]"
                show = self.queue.get()

            logging.info(f"{selected_queue_msg} Playing {show.song_name}")
            await self.play_show(show)
            logging.info(f"{selected_queue_msg} Finished {show.song_name}")


    def get_queue(self):
        """Gets the current view only queue that reflects the order of which songs are played next"""
        return list(self.request_queue.queue) + list(self.queue.queue)
    
    async def play_show(self, show: LightShow):
        # Preprocess the cues
        logging.debug("Preprocessing cues")
        cues = self.preprocess_show(show.light_cues)

        logging.debug(f"Loading audio {show.music_file}")
        sound = pygame.mixer.Sound(str(show.music_file))

        logging.debug(f"Playing audio {show.music_file}")
        channel = sound.play()  # non-blocking

        start = time()
        for timestamp in cues:
            try:
                now = time() - start

                if timestamp > now:
                    logging.info(f"Waiting for {timestamp}, it is currently {now}")
                    await asyncio.sleep(timestamp - now)

                now = time() - start
                events = cues[timestamp]
                futures = []
                for event in events:
                    id = event['id']
                    state = event['state']
                    logging.info(f"{timestamp}: {id} -> {state}\t\t({now})")
                    futures.append(self.send_state(id, state))
                await asyncio.gather(*futures)

            except Exception as e:
                logging.error(e)
                logging.error(e.with_traceback())
                return

        # Wait for the audio to finish
        while channel.get_busy():
            await asyncio.sleep(0.05)

        logging.info("Done with song!")



    async def serve(self):
        logging.info(f"Starting websocket server: ws://{self.host}:{self.port}")
        async with serve(self.handle_connect, self.host, self.port) as server:
            await server.serve_forever()

    def load_show(self, show_name: str) -> LightShow:
        show_path = Path(__file__).parent.parent / "shows" / show_name
        light_cues_path = show_path / f"{show_name}.json"
        music_file_path = show_path / f"{show_name}.wav"

        with open(light_cues_path, 'r') as light_cues_file:
            light_cues = json.load(light_cues_file)

        # Validate that light_cues is a list of dicts with expected keys
        if not isinstance(light_cues, list):
            raise ValueError(f"{light_cues_path} does not contain a JSON array (list) of cues.")

        expected_keys = {"id", "state", "t"}
        for idx, elem in enumerate(light_cues):
            if not isinstance(elem, dict):
                raise ValueError(f"Element at index {idx} in {light_cues_path} is not a JSON object/dict.")
            missing = expected_keys - set(elem.keys())
            if missing:
                raise ValueError(f"Element at index {idx} in {light_cues_path} missing keys: {missing}")

        if not music_file_path.exists():
            raise FileNotFoundError(f"{music_file_path} not found!")

        return LightShow(show_name, music_file_path, light_cues)

    def load_playlist(self) -> bool:
        """
        Attempts to reload the playlist from disk.
        Returns True if successful, False if the file was being edited.
        On failure, the existing playlist remains unchanged.
        """
        try:
            with open(self.playlist_path, 'r') as playlist_file:
                content = playlist_file.read()
                if not content.strip():
                    logging.warning("Playlist file is empty, keeping previous playlist")
                    return False
                show_names = json.loads(content)
                new_playlist = []
                for show_name in show_names:
                    try:
                        new_playlist.append(self.load_show(show_name))
                    except Exception as e:
                        logging.error(f"Error loading show {show_name}: {e}")
                        continue
                self.playlist = new_playlist
                logging.info("Playlist reloaded successfully")
                return True
        except json.JSONDecodeError as e:
            logging.warning(f"Playlist file appears to be mid-edit (invalid JSON): {e}")
            return False
        except FileNotFoundError:
            logging.error("Playlist file not found")
            return False
        except Exception as e:
            logging.warning(f"Error loading playlist: {e}")
            return False

async def main():
    """
    Starts the WebSocket server.
    """
    config_path = Path(__file__).parent.parent / "config"
    id_mapping_path = config_path / "id_mapping.json"
    with open(id_mapping_path, "r") as id_mapping_file:
        id_mapping = json.load(id_mapping_file)
    
    playlist_path = config_path / "playlist.json"
    
    # Make a schedule with datetime that just represents time of day with no dates

    schedule = DailySchedule(datetime.time(17, 0), datetime.time(23, 0))
    host = "0.0.0.0"
    port = 8765

    server = WebsocketServer(host, port, id_mapping, playlist_path, schedule)
    await asyncio.gather(server.serve(), server.run())

if __name__ == "__main__":
    asyncio.run(main())

