# 故障排除

Aivonx Proxy 的常見問題和解決方案。

## 日誌與診斷

### 日誌檔案位置

- **一般日誌**：`logs/django.json`（JSON 格式）
- **代理日誌**：`logs/proxy.json`（JSON 格式）
- **錯誤日誌**：`logs/django_error.log`（僅 ERROR 級別）
- **除錯日誌**：`logs/django_debug.log`（DEBUG 級別，如果啟用）

### 檢視日誌

```bash
# Tail 一般日誌
tail -f logs/django.json | jq

# Tail 代理日誌
tail -f logs/proxy.json | jq

# 檢視錯誤日誌
tail -f logs/django_error.log

# Docker 日誌
docker-compose logs -f django
```

## 常見問題

### 應用程式無法啟動

#### 檢查資料庫連線

```bash
# 驗證 PostgreSQL 正在執行
docker-compose ps postgres

# 測試連線
psql -h localhost -U user -d app_db

# 檢查環境變數
env | grep POSTGRES
```

**解決方案**：確保 PostgreSQL 服務正在執行，且 `.env` 或環境變數中的憑證正確。

#### 檢查 Redis 連線

```bash
# 驗證 Redis 正在執行
docker-compose ps redis

# 測試連線
redis-cli -h localhost ping

# 檢查環境變數
echo $REDIS_URL
```

**解決方案**：確保 Redis 服務正在執行，且 `REDIS_URL` 正確設定。

#### 缺少 SECRET_KEY

**錯誤**：`ValueError: DJANGO_SECRET_KEY environment variable is required`

**解決方案**：在您的環境中設定 `DJANGO_SECRET_KEY`：

```bash
export DJANGO_SECRET_KEY="your-secret-key-here"
# 或在 .env 檔案中
echo "DJANGO_SECRET_KEY=your-secret-key-here" >> .env
```

### 節點健康檢查失敗

#### 症狀

- 節點在 `/api/proxy/state` 中顯示為非活躍
- 請求返回「no healthy nodes available」

#### 診斷

```bash
# 直接檢查節點健康
curl http://node-address:11434/api/health

# 檢查代理狀態
curl http://localhost:8000/api/proxy/state

# 檢查活躍請求
curl http://localhost:8000/api/proxy/active-requests
```

#### 解決方案

1. **網路連線**：確保代理可以到達節點
   ```bash
   ping node-address
   telnet node-address 11434
   ```

2. **防火牆規則**：檢查連接埠 11434（或配置的連接埠）是否開放

3. **節點已關閉**：在節點上重新啟動 Ollama 服務
   ```bash
   systemctl restart ollama  # 在 Linux 上
   ```

4. **強制重新整理**：健康檢查每分鐘執行一次，或手動觸發：
   ```python
   from proxy.utils.proxy_manager import get_global_manager
   mgr = get_global_manager()
   mgr.refresh_from_db()
   ```

### 快取問題

#### 過時快取資料

**症狀**：狀態端點顯示過時資訊

**解決方案**：清除 Redis 快取

```bash
# 使用 Django shell
python src/manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 或直接使用 Redis
redis-cli FLUSHDB
```

#### Redis 連線錯誤

**錯誤**：`ConnectionError: Error connecting to Redis`

**解決方案**：
1. 驗證 Redis 正在執行
2. 檢查 `REDIS_URL` 格式：`redis://host:port/db`
3. 測試連線：
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

### 串流問題

#### 串流回應無法運作

**症狀**：回應完全緩衝而非串流

**原因**：使用 WSGI 伺服器而非 ASGI

**解決方案**：使用 uvicorn 或 gunicorn 與 uvicorn 工作者：

```bash
# 開發
uvicorn aivonx.asgi:application --reload

# 生產
gunicorn aivonx.asgi:application -k uvicorn.workers.UvicornWorker --workers 4
```

### 靜態檔案未載入

#### 開發

**解決方案**：確保 `DEBUG=True` 或執行 `collectstatic`

```bash
python src/manage.py collectstatic --noinput
```

#### 生產

**解決方案**：驗證 WhiteNoise 中介軟體已啟用且靜態檔案已收集：

```bash
python src/manage.py collectstatic --noinput --clear
```

### 資料庫遷移問題

#### 假裝遷移

如果遷移已手動應用：

```bash
python src/manage.py migrate --fake app_name migration_name
```

#### 重設遷移（僅開發）

⚠️ **警告**：這將刪除所有資料

```bash
# 刪除資料庫
dropdb app_db

# 重新建立
createdb app_db

# 執行遷移
python src/manage.py migrate
```

### 權限錯誤

#### API 端點上的 403 Forbidden

**原因**：需要認證但未提供

**解決方案**：包含認證權杖：

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/proxy/config
```

或透過網頁 UI 使用會話認證登入。

### 效能問題

#### 高記憶體使用

**解決方案**：
1. 減少工作者數量
2. 啟用 Redis 持久性
3. 清除舊日誌檔案
4. 檢查自訂程式碼中的記憶體洩漏

#### 慢回應

**診斷**：
```bash
# 檢查節點延遲
curl http://localhost:8000/api/proxy/state | jq '.latencies'

# 檢查活躍請求計數
curl http://localhost:8000/api/proxy/active-requests
```

**解決方案**：
1. 新增更多節點
2. 切換到 `lowest_latency` 策略
3. 增加工作者計數
4. 檢查到節點的網路延遲

## 除錯模式

### 啟用除錯日誌

在 `src/aivonx/settings.py` 中，暫時增加日誌級別：

```python
LOGGING = {
    # ...
    'loggers': {
        'proxy': {
            'handlers': ['console', 'proxy_file'],
            'level': 'DEBUG',  # 從 INFO 變更
            'propagate': False,
        },
    },
}
```

### Django 除錯工具列

對於開發，安裝 Django 除錯工具列：

```bash
pip install django-debug-toolbar
```

## 獲取幫助

1. **檢查日誌**：檢視日誌檔案以尋找錯誤訊息
2. **API 狀態**：使用 `/api/proxy/state` 檢查管理員狀態
3. **健康檢查**：驗證所有服務都健康
4. **GitHub 問題**：在儲存庫上搜尋或開啟問題

## 除錯的有用命令

```bash
# 系統檢查
python src/manage.py check --deploy

# 顯示目前設定
python src/manage.py diffsettings

# 資料庫 shell
python src/manage.py dbshell

# 具有 Django 上下文的 Python shell
python src/manage.py shell

# 顯示 URL 模式
python src/manage.py show_urls  # 需要 django-extensions

# 測試 Redis 連線
redis-cli -h localhost ping

# 測試 PostgreSQL 連線
psql -h localhost -U user -d app_db -c 'SELECT 1;'
```