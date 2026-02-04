# Dockerfile for Insurance WhatsApp Agent
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn uvicorn[standard]

# Copy application code (uses .dockerignore to exclude unnecessary files)
COPY . .

# Default port
ENV PORT=3000

# Expose port
EXPOSE $PORT

# Run with gunicorn using uvicorn workers for async support
CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 120 main:app
