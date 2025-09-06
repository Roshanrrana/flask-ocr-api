# Dockerfile for Render deployment (installs tesseract + poppler + python deps)
FROM python:3.11-slim

# Install system packages required for OCR and pdf->image conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Render provides a $PORT environment variable. Expose and use it.
ENV PORT=10000

# Start using gunicorn and bind to dynamic PORT
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT api:app"]
