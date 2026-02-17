# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY paperbanana/ ./paperbanana/
COPY prompts/ ./prompts/
COPY configs/ ./configs/
COPY data/ ./data/

# Copy built frontend
COPY --from=frontend-build /app/frontend/out ./frontend/out

# Set environment variables
ENV FRONTEND_DIR=/app/frontend/out
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "paperbanana.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
