FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
libpq-dev \
gcc && rm -rf /var/lib/apt/lists/*

# Installing uv globally
RUN pip install --no-cache-dir uv
# Copy requirements file
COPY pyproject.toml ./
# Install python dependencies
RUN uv pip install --system --no-cache . gunicorn uvicorn

# Copy application source code
COPY . .

EXPOSE 8000
# Run with Gunicorn using Uvicorn workers
CMD ["gunicorn", "backend.app:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]