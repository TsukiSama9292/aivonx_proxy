# 疑難排解

常見問題與解法。

## 日誌與診斷

### 日誌檔位置

- **一般日誌**：`logs/django.json`
- **Proxy 日誌**：`logs/proxy.json`
- **錯誤日誌**：`logs/django_error.log`
- **除錯日誌**：`logs/django_debug.log`（若啟用）

### 檢視日誌

```bash
# 追蹤一般日誌
tail -f logs/django.json | jq

# 追蹤 proxy 日誌
tail -f logs/proxy.json | jq

# 檢視錯誤日誌
tail -f logs/django_error.log

# Docker 日誌
docker-compose logs -f django
```

## 常見問題與解法

### 應用無法啟動

#### 檢查資料庫連線

```bash
# 確認 PostgreSQL 運行
docker-compose ps postgres

# 測試連線
psql -h localhost -U user -d app_db

# 檢查環境變數
env | grep POSTGRES
```

**解法**：確保 PostgreSQL 正常運作且 .env 或環境變數中的認證正確。

#### 檢查 Redis 連線

```bash
# 確認 Redis 運行
docker-compose ps redis

# 測試連線
redis-cli -h localhost ping

# 檢查環境變數
echo $REDIS_URL
```

**解法**：確保 Redis 運作且 `REDIS_URL` 設定正確。

#### 缺少 SECRET_KEY

**錯誤**：`ValueError: DJANGO_SECRET_KEY environment variable is required`

**解法**：設定 `DJANGO_SECRET_KEY`：

```bash
export DJANGO_SECRET_KEY="your-secret-key-here"
# 或寫入 .env
echo "DJANGO_SECRET_KEY=your-secret-key-here" >> .env
```

### 節點健康檢查失敗

#### 症狀

- `/api/proxy/state` 顯示節點為非活躍
- 請求回應 "no healthy nodes available"

#### 判斷方式

```bash
# 直接檢查節點健康
curl http://node-address:11434/api/health

# 檢查 proxy 狀態
curl http://localhost:8000/api/proxy/state

# 檢查活動請求數
curl http://localhost:8000/api/proxy/active-requests
```

#### 解法
1. 檢查網路與連線
2. 檢查防火牆是否開放 11434 埠號
3. 重新啟動 Ollama 節點服務
4. 強制更新代理狀態（可透過 get_global_manager() 呼叫 refresh）

### 快取問題

#### 快取資料不一致

**症狀**：狀態端點顯示過時資訊

**解法**：清除 Redis 快取

```bash
python src/manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 或直接使用 redis
redis-cli FLUSHDB
```

### 串流問題

#### 串流回應被緩衝

**原因**：使用 WSGI 而非 ASGI

**解法**：使用 uvicorn 或 gunicorn 搭配 uvicorn worker

```bash
# 開發
uvicorn aivonx.asgi:application --reload

# 生產
gunicorn aivonx.asgi:application -k uvicorn.workers.UvicornWorker --workers 4
```

### 靜態檔案無法載入

開發環境：確認 `DEBUG=True` 或執行 `collectstatic`

生產環境：確認 WhiteNoise 已啟用並完成收集靜態檔

```bash
python src/manage.py collectstatic --noinput --clear
```

### 資料庫遷移問題

如需略過已手動套用的遷移：

```bash
python src/manage.py migrate --fake app_name migration_name
```

重置遷移（僅開發）會清除資料：

```bash
dropdb app_db
createdb app_db
python src/manage.py migrate
```

### 權限錯誤（403）

**原因**：需要驗證但未提供

**解法**：在請求中加入驗證 Token，或透過 Web UI 使用 Session 登入。

### 效能問題

高記憶體或慢速回應的診斷步驟與解法，請參考原始疑難排解區塊。