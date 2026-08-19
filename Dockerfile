# Multi-stage Dockerfile for AI Operations Copilot (C++ & Python)

# Stage 1: C++ Compiler
FROM gcc:12 AS builder
WORKDIR /build
COPY cpp_engine/ ./cpp_engine/
RUN mkdir -p /build/app/lib && \
    make -C cpp_engine

# Stage 2: Python Runtime
FROM python:3.11-slim
WORKDIR /app

# Install runtime tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy C++ compiled library from builder
COPY --from=builder /build/app/lib/ /app/app/lib/

# Copy application source
COPY app/ /app/app/
COPY tests/ /app/tests/

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
