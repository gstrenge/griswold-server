# Griswold Server

A WebSocket server for synchronized Christmas light shows. Plays audio and sends timed light cues to connected controllers.

## Project Structure

```
griswold-server/
├── src/
│   └── server.py          # Main server application
├── config/
│   ├── id_mapping.json    # Maps friendly IDs to controller IDs
│   └── playlist.json      # List of shows to play in order
├── shows/
│   └── <show_name>/
│       ├── <show_name>.json   # Light cue timings
│       └── <show_name>.wav    # Audio file
├── requirements.txt
├── Dockerfile
└── docker-compose.yaml
```

## Configuration

### `config/id_mapping.json`

Maps human-readable light IDs to the raw controller IDs:

```json
{
  "device1-1": "1A",
  "device1-2": "SNOWMACHINE_1"
}
```

### `config/playlist.json`

List of show names to cycle through:

```json
["white_christmas", "home_alone", "rudolph"]
```

The playlist is reloaded after each full cycle, so you can add new shows without restarting the server.

### Adding a Show

1. Create a folder in `shows/` matching the show name
2. Add `<show_name>.json` with light cues:
   ```json
   [
     {"t": 0.0, "id": "1A", "state": 1.0},
     {"t": 2.5, "id": "1A", "state": 0.0}
   ]
   ```
   - `t`: Time in seconds from start
   - `id`: Light ID (from id_mapping)
   - `state`: 0.0 (off) to 1.0 (on)
3. Add `<show_name>.wav` audio file
4. Add the show name to `config/playlist.json`

---

## Windows (No Docker)

### Prerequisites

- Python 3.10+

### Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python src/server.py
```

The server starts on `ws://localhost:8765` by default.

## Ubuntu (No Docker)

### Prerequisites

- Python 3.10+
- On Linux: `sudo apt install libasound2-dev`

### Setup

```bash
cd griswold-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python src/server.py
```

---

## Running with Docker (Linux only for audio)

> ⚠️ **Warning**: This currently does not work, use native instructions.

> ⚠️ **Note**: Audio playback from Docker requires Linux. On Windows/macOS, Docker containers cannot easily access audio hardware. Use native Python instead.

### Prerequisites

- Docker & Docker Compose

### Build and Run

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up -d --build

# View logs
docker compose logs -f server

# Stop
docker compose down
```

### Volumes

The `config/` and `shows/` directories are mounted as volumes, so you can update playlists and add shows without rebuilding the container.

---

## Console Commands

While the server is running, you can enter commands:

| Command | Description |
|---------|-------------|
| `c` | List connected controller IDs |
| `q` | Add a test show to the request queue |
| `snow` | Turn on snow machine + spotlights |
| `nosnow` | Turn off snow machine + spotlights |
| `s,<id>,<state>` | Set light state (e.g., `s,1A,1.0`) |
| `sr,<raw_id>,<state>` | Set state by raw controller ID |

---

## Schedule

The server only plays shows during scheduled hours (default: 5 PM - 11 PM). Outside this window, it sleeps and checks every 60 seconds.

To modify, edit the schedule in `src/server.py`:

```python
schedule = DailySchedule(datetime.time(17, 0), datetime.time(23, 0))
```

---

## WebSocket Protocol

Controllers connect and register their IDs:

```json
{"ids": ["controller-abc123", "controller-def456"]}
```

Server sends state updates:

```json
{"id": "controller-abc123", "state": 1.0}
```

