# Job Search AI Agent - Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r jobagent && useradd -r -g jobagent jobagent

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.sh .

# Create necessary directories
RUN mkdir -p /app/config /app/output /app/logs && \
    chown -R jobagent:jobagent /app

# Switch to non-root user
USER jobagent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.config.settings import config; from src.core.agent import JobSearchAgent; agent = JobSearchAgent(); exit(0 if agent.health_check()['overall'] else 1)"

# Default command
CMD ["python", "-m", "src.main", "--schedule", "07:00"]