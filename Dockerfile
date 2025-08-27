# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set to run as root as requested
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy environment file
COPY .env .

# Copy all Python application files
COPY app.py .
COPY config.py .
COPY git_operations.py .
COPY github_api.py .
COPY tool_contracts.py .
COPY tool_execution_engine.py .
COPY intent_classification.py .
COPY main.py .

# Create config directory (referenced in config.py)
RUN mkdir -p config

# Create repos directory for git operations
RUN mkdir -p repos

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=7309
ENV FASTAPI_PORT=7309

# Expose port 7309
EXPOSE 7309

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7309/ || exit 1

# Run FastAPI application
CMD ["python", "app.py"]