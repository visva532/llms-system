FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install OS-level dependencies for some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port Railway will use
EXPOSE 8000

# Start the app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
