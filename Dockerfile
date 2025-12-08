FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for building simpleaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose websocket port
EXPOSE 8765

CMD ["python", "src/server.py"]

