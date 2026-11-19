FROM python:3.10-slim

# 從官方鏡像快速複製 uv（GitHub Actions 上秒抓）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# 先複製 requirements.txt 利用 Docker 快取層
COPY requirements.txt .

# 直接用 uv 快速將套件裝入 system python（比 pip 快 10~50 倍，免除 venv 搬移耗時）
RUN uv pip install -r requirements.txt

# 複製應用程式代碼
COPY . .

EXPOSE 7860

CMD ["python", "-m", "timevest.main"]
