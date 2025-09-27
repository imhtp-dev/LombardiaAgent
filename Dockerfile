# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PYTHONPATH=/app \
      PORT=8000

WORKDIR /app

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y \
      gcc g++ ffmpeg libsndfile1 portaudio19-dev python3-dev curl \
      && rm -rf /var/lib/apt/lists/*

# Copy requirements and use cache mount for pip
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
      pip install --upgrade pip && \
      pip install -r requirements.txt

# Download NLTK data as root (before switching users)
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

  # Copy application code
  COPY . .

# Create directories and download models
RUN mkdir -p logs recordings data
RUN python -c "import torch; torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=True)"

# Create non-root user and set permissions
RUN groupadd -r pipecat && useradd -r -g pipecat pipecat
RUN chown -R pipecat:pipecat /app
RUN chown -R pipecat:pipecat /root/nltk_data 2>/dev/null || true

# Switch to non-root user
USER pipecat

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:$PORT/health || exit 1

EXPOSE $PORT

# Command with all optimizations
CMD ["python", "-m", "uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--backlog", "2048","--limit-concurrency", "10"]