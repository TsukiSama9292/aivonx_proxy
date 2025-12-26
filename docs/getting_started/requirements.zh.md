# 需求

## 系統需求

- **Python**：>=3.12, <3.13
- **作業系統**：Linux、macOS 或 Windows（建議在生產環境使用 Linux）

## 核心相依套件

所有專案相依套件均指定在 `pyproject.toml` 中。關鍵套件包括：

- **Django**：>=5.2.8 - Web 框架
- **Django REST Framework**：帶認證的 API 框架
- **drf-spectacular**：OpenAPI 3 架構生成
- **uvicorn / gunicorn**：ASGI/WSGI 伺服器選項
- **Redis**：>=7.1.0 - 快取和會話儲存
- **django-redis**：Redis 快取後端
- **PostgreSQL**：生產資料庫（psycopg2-binary）
- **httpx**：現代非同步 HTTP 客戶端
- **APScheduler**：背景任務排程

## 開發工具

建議用於開發：
- `ipykernel`：Jupyter 核心支援
- `jupyterlab`：互動式開發環境
- `pytest`：測試框架
- `mkdocs` 和 `mkdocs-material`：文件生成

## 安裝

使用 `uv` 安裝（推薦）：

```bash
uv sync
```

或使用 pip：

```bash
pip install -e .[dev]
```