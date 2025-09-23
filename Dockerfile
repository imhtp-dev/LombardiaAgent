# Dockerfile for Pipecat Healthcare Agent
# Optimized for Azure Container Apps deployment with concurrent call handling

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies required for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs recordings data

# Download and cache Silero VAD model (recommended by Pipecat for performance)
RUN python -c "import torch; torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=True)"

# Create non-root user for security
RUN groupadd -r pipecat && useradd -r -g pipecat pipecat
RUN chown -R pipecat:pipecat /app
USER pipecat

# Health check for Azure Container Apps
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port
EXPOSE $PORT

# Start command optimized for concurrent calls
CMD ["python", "-m", "uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop"]

