# 設定參考

主要設定檔位於 `src/aivonx/settings.py`。

## 核心設定

### Debug 模式

- **設定**：`DEBUG`
- **環境變數**：`DJANGO_DEBUG`
- **預設**：`True`（開發）
- **生產**：請設為 `false`

```bash
DJANGO_DEBUG=false
```

### Secret Key

- **設定**：`SECRET_KEY`
- **環境變數**：`DJANGO_SECRET_KEY`
- **必要性**：生產環境必填

```bash
DJANGO_SECRET_KEY=your-secret-key-here
```

⚠️ 請勿將 secret key 提交到版本控制。

### Allowed Hosts

- **設定**：`ALLOWED_HOSTS`
- **環境變數**：`DJANGO_ALLOWED_HOSTS`
- **格式**：逗號分隔

```bash
DJANGO_ALLOWED_HOSTS=example.com,api.example.com
```

## 資料庫

預設使用 PostgreSQL，透過環境變數設定：

```bash
POSTGRES_DB=app_db
POSTGRES_USER=user
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

## 快取

Redis 用於快取與 session：

```bash
REDIS_URL=redis://redis:6379/1
```

## 安全

### CORS

```bash
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

### CSRF

```bash
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://app.example.com
```

## 靜態檔案

- `STATIC_URL`：`/static/`
- `STATIC_ROOT`：`{BASE_DIR}/staticfiles`
- `STATICFILES_DIRS`：`[{BASE_DIR}/ui/static]`

使用 WhiteNoise 提供靜態檔案服務，並透過 `collectstatic` 收集。

## 日誌

日誌檔：
- `logs/django.json`、`logs/proxy.json`、`logs/django_error.log`

## API 文件設定（drf-spectacular）

示例：

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'aivonx proxy API',
    'DESCRIPTION': 'API documentation for aivonx proxy',
    'VERSION': '1.0.0',
}
```

## REST Framework

認證支援：JWT（SimpleJWT）、Session、Token。

預設權限：`IsAuthenticated`（未顯式設定為 `AllowAny` 的端點需驗證）

分頁：`LimitOffsetPagination`，預設 page size: 100