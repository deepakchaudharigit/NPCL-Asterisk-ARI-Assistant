# Multi-stage Docker build for NPCL Voice Assistant
# Optimized for production deployment with security and performance

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Set labels for metadata
LABEL org.opencontainers.image.title="NPCL Voice Assistant"
LABEL org.opencontainers.image.description="AI-powered voice assistant for power utility customer service"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}
LABEL org.opencontainers.image.vendor="NPCL"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    portaudio19-dev \
    python3-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-test.txt ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r voiceassistant && useradd -r -g voiceassistant voiceassistant

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY .env.example ./.env

# Create necessary directories
RUN mkdir -p sounds/temp recordings logs \
    && chown -R voiceassistant:voiceassistant /app

# Copy startup script
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Switch to non-root user
USER voiceassistant

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]