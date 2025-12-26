# 部署選項

Aivonx Proxy 支援多種部署策略，以符合不同需求與環境。

## 1. Docker Compose（開發推薦）

使用專案提供的 `docker-compose.yml` 做一鍵部署：

```bash
docker-compose up -d
```

包含服務：
- Django 應用
- PostgreSQL 資料庫
- Redis 快取
- Ollama 服務（可選）

## 2. Kubernetes（生產）

生產環境建議使用 Kubernetes：
- 使用託管的 PostgreSQL 與 Redis
- 設定 Horizontal Pod Autoscaler
- 設定資源限制與請求
- 使用 Ingress 做 SSL/TLS 終端

## 3. ASGI 伺服器（適合串流）

若需要即時串流或 WebSocket 支援，使用 ASGI：

```bash
# 使用 uvicorn
uvicorn aivonx.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# 或搭配 gunicorn 與 uvicorn workers
gunicorn aivonx.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
```

## 4. WSGI 伺服器（傳統部署）

同步工作負載可使用 WSGI：

```bash
gunicorn aivonx.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## 環境變數（重點）

必備或重要環境變數（詳細請參考 `src/aivonx/settings.py`）：

### 生產需要
- `DJANGO_SECRET_KEY`：必要
- `DJANGO_DEBUG`：生產請設為 `false`
- `DJANGO_ALLOWED_HOSTS`：允許的主機列表

### 資料庫
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

### 快取
- `REDIS_URL`（預設：`redis://redis:6379/1`）

### 安全
- `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `ROOT_PASSWORD`

## 生產檢查清單

- 設定強隨機 `DJANGO_SECRET_KEY`
- 關閉 debug 模式 (`DJANGO_DEBUG=false`)
- 設定正確的 `ALLOWED_HOSTS`
- 使用託管的 PostgreSQL 與 Redis
- 設定 SSL/TLS
- 配置日誌與監控
- 變更預設 `root` 密碼
- 設定自動備份
- 設定防火牆規則