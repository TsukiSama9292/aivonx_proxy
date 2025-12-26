# 部署選項

Aivonx Proxy 支援多種部署策略，以符合不同需求與環境。

## 1. Docker Compose（開發推薦）

使用專案提供的 `docker-compose.yml` 做一鍵部署：

```bash
docker-compose up -d
```

包含服務：
- Django 應用伺服器
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

## 環境變數

關鍵環境變數（詳細請參考 `src/aivonx/settings.py`）：

### 生產需要

- `DJANGO_SECRET_KEY`：**必要** - Django 的密碼學秘密
- `DJANGO_DEBUG`：生產請設為 `false`
- `DJANGO_ALLOWED_HOSTS`：允許的主機名稱列表

### 資料庫配置

- `POSTGRES_DB`：資料庫名稱（預設：`app_db`）
- `POSTGRES_USER`：資料庫使用者（預設：`user`）
- `POSTGRES_PASSWORD`：資料庫密碼（預設：`password`）
- `POSTGRES_HOST`：資料庫主機（預設：`postgres`）
- `POSTGRES_PORT`：資料庫連接埠（預設：`5432`）

### 快取配置

- `REDIS_URL`：Redis 連線 URL（預設：`redis://redis:6379/1`）

### 安全配置

- `DJANGO_CORS_ALLOWED_ORIGINS`：允許的 CORS 來源
- `DJANGO_CSRF_TRUSTED_ORIGINS`：受信任的 CSRF 來源
- `ROOT_PASSWORD`：預設 `root` 使用者的密碼

## 生產檢查清單

- [ ] 設定強隨機 `DJANGO_SECRET_KEY`
- [ ] 關閉 debug 模式 (`DJANGO_DEBUG=false`)
- [ ] 設定正確的 `ALLOWED_HOSTS`
- [ ] 使用託管的 PostgreSQL 與 Redis
- [ ] 設定 SSL/TLS 憑證
- [ ] 配置日誌與監控
- [ ] 變更預設 `root` 密碼
- [ ] 設定自動備份
- [ ] 設定防火牆規則
