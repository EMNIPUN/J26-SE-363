# ==============================================================================
# PERFORMANCE ASSESSMENT AGENT - DOCKERFILE
# Completely decoupled container runtime for the assessment microservice
# ==============================================================================

FROM python:3.11-slim AS base

# Install system dependencies (git for GitSandboxRunner, libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy isolated requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create package structure so imports resolve cleanly:
# from app.agents.performance_assessment...
RUN mkdir -p /app/app/agents/performance_assessment && \
    touch /app/app/__init__.py /app/app/agents/__init__.py

# Copy agent code into the container
COPY . /app/app/agents/performance_assessment/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    COM_AGENT_ENV=production \
    PORT=8002

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "app.agents.performance_assessment.server:app", "--host", "0.0.0.0", "--port", "8002"]
