## aivonx_proxy — Ollama 反向代理

輕量級的 Ollama 模型節點反向代理與高可用（HA）管理服務，提供統一的 API 路由、節點管理、模型發現與串流代理能力。

<p align="center">
  <img
    src="./asstes/images/AIVONX_PROXY.png"
    alt="AIVONX Proxy"
    width="200"
    height="200"
  />
</p>

<p align="center">
  <a href="https://github.com/TsukiSama9292/aivonx_proxy/commits/main">
    <img src="https://img.shields.io/github/last-commit/TsukiSama9292/aivonx_proxy" alt="Last Commit">
  </a>
  <a href="https://github.com/TsukiSama9292/aivonx_proxy/actions/workflows/tests.yml">
    <img src="https://github.com/TsukiSama9292/aivonx_proxy/actions/workflows/tests.yml/badge.svg" alt="CI Status">
  </a>
</p>

**主要功能**
- 節點管理：新增/移除/編輯 Ollama 節點，並維護活動/備援池。
- Proxy API：在 `/api/proxy` 之下路由請求到可提供該模型的節點，支援串流回應。
- 模型發現：列出各節點可用的模型（`GET /api/tags`）。
- HA / 負載策略：`least_active`（預設）與 `lowest_latency`。
- 健康檢查：`GET /api/proxy`（任一節點可用即視為服務可用）。

## Quick Start

以下流程以專案根目錄為工作目錄（含 `docker-compose.yml`）。建議使用 Docker Compose 取得快速、可複現的環境。

1. 使用 Docker Compose 啟動服務（建議）：

```bash
docker compose up -d
```

2. 開啟瀏覽器：

- 管理介面（Web UI）：http://localhost:8000
- 互動 API 文件： http://localhost:8000/swagger 或 http://localhost:8000/redoc

3. 預設管理員帳號（請在上線之前變更）：

- 使用者：`root`
- 密碼：`changeme`

要在部署時覆寫初始 `root` 密碼，請在專案根目錄的 `.env` 檔（與 `src/` 同層）設定：

```env
ROOT_PASSWORD=your_secure_password_here
```

### 使用 `uv` 執行 Python 任務（必要）

專案慣用 `uv` 這組開發/執行工具，請用 `uv run` 來執行 Python entrypoints，以確保環境與執行參數一致：

```bash
# 安裝/同步開發環境
uv sync

# 執行資料庫遷移
uv run src/manage.py migrate

# 收集靜態檔案（變更靜態資源後執行）
uv run src/manage.py collectstatic --noinput

# 測試
uv run src/manage.py test proxy.tests

# 開發（ASGI，支援串流）：
uv run main.py --reload --port 8000
```

> 注意：串流與即時代理建議以 ASGI 伺服器（例如 `uvicorn`）執行以避免 WSGI 緩衝。

## 部署與環境變數

主要部署選項：
- Docker Compose（開發/簡易部署）
- Kubernetes（生產，搭配 managed DB 與 Redis）
- ASGI（推薦用於串流）或 WSGI（同步工作負載）

重要環境變數（亦可於 `src/aivonx/settings.py` 檢視更完整清單）：

- `DJANGO_SECRET_KEY`：生產環境「必須」設定
- `DJANGO_DEBUG`：生產請設定為 `False`
- `DJANGO_ALLOWED_HOSTS`：允許的 host 清單
- `ROOT_PASSWORD`：預設管理員密碼
- 資料庫：`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- 快取：`REDIS_URL`

生產檢查清單（摘要）：
- 設定強密鑰 `DJANGO_SECRET_KEY`
- 關閉 `DEBUG`
- 設定 `ALLOWED_HOSTS`
- 使用生產級 PostgreSQL 與 Redis
- 設定 SSL/TLS 與監控/備份
- 變更預設 `root` 密碼

## API 與核心端點簡介

互動文件啟動後可在 `/swagger` 或 `/redoc` 看到完整 API 規格。常用端點示例：

- 健康檢查：`GET /api/health`
- 列出模型：`GET /api/tags`
- Proxy 產生：`POST /api/generate`, `POST /api/chat`
- Embeddings：`POST /api/embed`, `POST /api/embeddings`
- Proxy 狀態：`GET /api/proxy/state`
- 節點管理：`/api/proxy/nodes`（CRUD）

詳細 API 規格請參閱文件或啟動後的互動文件。

## 開發者說明

- 程式源碼：`src/`
- Proxy 實作範圍：`src/proxy/`
- 設定檔：`src/aivonx/settings.py`

開發流程建議：

```bash
# 同步環境
uv sync

# 遷移
uv run src/manage.py migrate

# 執行測試
uv run src/manage.py test
```

請參閱專案貢獻指南（位於 `docs/`），以了解貢獻步驟、程式碼風格和 PR 指南。