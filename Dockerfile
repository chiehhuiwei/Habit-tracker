# ── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.10-slim AS builder

# Pull the official uv binary (avoids pip-installing uv itself)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Compile bytecode and use copy link-mode so the venv works after COPY
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install Python dependencies using a build-time cache mount.
# This layer is only invalidated when requirements.txt changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r requirements.txt

# ── Stage 2: lean runtime image ─────────────────────────────────────────────
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies (fonts for matplotlib Chinese characters)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bring in the pre-built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the rest of the application
COPY . .

# Expose port 7860 for Gradio
EXPOSE 7860

# Run the app via the venv Python
CMD ["python", "app.py"]
