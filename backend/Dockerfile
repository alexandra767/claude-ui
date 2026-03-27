FROM python:3.11-slim

WORKDIR /app

# System deps: ffmpeg for security camera, curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3001

CMD ["python3", "main.py"]
