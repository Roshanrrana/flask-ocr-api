# Dockerfile for Render deployment (installs Tesseract + Poppler + Python deps)
FROM python:3.11-slim

# Install system packages required for OCR and PDF->image conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy python dependencies
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Render's PORT environment variable
ENV PORT=10000

# Use gunicorn to run the Flask app (ensure your Flask app file is named api.py and the app object is 'app')
CMD ["sh", "-c", "gunicorn --workers 1 --bind 0.0.0.0:$PORT api:app"]
