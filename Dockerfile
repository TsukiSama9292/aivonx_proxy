# --- 第一階段：構建環境 (Build Stage) ---
FROM python:3.12-alpine AS builder

# 安裝構建基礎工具
RUN apk add --no-cache curl bash build-base postgresql-dev libpq-dev

# 安裝 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

# 安裝依賴環境
RUN uv sync --frozen --no-dev

# --- 第二階段：運行環境 (Runtime Stage) ---
FROM python:3.12-alpine

# 1. 升級系統套件與修復 pip 漏洞雜訊
RUN apk upgrade --no-cache && \
    apk add --no-cache libpq && \
    python -m pip install --upgrade pip

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# 2. 從 builder 複製虛擬環境
COPY --from=builder /app/.venv /app/.venv
# 複製原始碼
COPY . .

# 3. 執行 Django 靜態檔案蒐集與清理冗餘檔案
RUN python src/manage.py collectstatic --noinput && \
    find . -name "*.pyc" -delete

# 建立非 root 使用者以提高安全性
RUN adduser -D appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python src/manage.py migrate && python main.py --workers 2"]