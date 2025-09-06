# Dockerfile for Render deployment (installs Tesseract + Poppler + Python deps)
FROM python:3.11-slim

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

ENV PORT=10000

CMD ["sh", "-c", "gunicorn --workers 1 --bind 0.0.0.0:$PORT api:app"]
