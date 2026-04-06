# Use Python 3.11 slim image for a smaller footprint
FROM python:3.11-slim

# Install system dependencies (ffmpeg is required for yt-dlp merging)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create necessary directories
RUN mkdir -p downloads cache

# The server port is set by Render's $PORT environment variable
# default to 8000 for local testing
EXPOSE 8000

# Start the uvicorn server
# We use the $PORT env variable provided by Render
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
