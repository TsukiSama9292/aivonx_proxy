# 環境需求

## 系統需求

- **Python**：>=3.12, <3.13
- **作業系統**：Linux、macOS 或 Windows（建議在生產環境使用 Linux）

## 核心相依套件

專案相依紀錄於 `pyproject.toml`。關鍵套件包括：

- **Django**：Web 框架
- **Django REST Framework**：API 框架
- **drf-spectacular**：OpenAPI 3 文件產生
- **uvicorn / gunicorn**：ASGI/WSGI 伺服器
- **Redis**：快取與 session 儲存
- **django-redis**：Redis 快取後端
- **PostgreSQL**（生產用，使用 `psycopg2-binary`）
- **httpx**：非同步 HTTP 客戶端
- **APScheduler**：背景工作排程

## 開發工具

建議開發工具：
- `ipykernel`、`jupyterlab`、`pytest`、`mkdocs` 與 `mkdocs-material`

## 安裝

建議使用 `uv` 管理器（專案提供）：

```bash
uv sync
```

或使用 pip 安裝開發依賴：

```bash
pip install -e .[dev]
```