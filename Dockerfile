# Use lightweight Python base image
FROM python:3.10-slim

# Prevent Python from writing pyc files & enable stdout/stderr immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (for PyMuPDF, numpy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install numpy first to avoid binary incompatibility
RUN pip install --no-cache-dir "numpy<2" \
    && pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Google Cloud Run automatically sets the PORT env variable
ENV PORT=8080

# Expose port (Cloud Run expects 8080)
EXPOSE 8080

# Start FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
