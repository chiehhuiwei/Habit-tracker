# ── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /app

# 安裝 curl 並透過官方獨立二進位安裝 uv（避免 ghcr.io 登入認證限制）
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install Python dependencies using a build-time cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r requirements.txt

# ── Stage 2: lean runtime image ─────────────────────────────────────────────
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Bring in the pre-built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the rest of the application
COPY . .

# FastAPI on 7860
EXPOSE 7860

CMD ["python", "-m", "timevest.main"]
