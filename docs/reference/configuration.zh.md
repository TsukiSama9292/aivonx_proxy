# 設定參考

主要設定檔位於 `src/aivonx/settings.py`。

## 核心設定

### Debug 模式

- **設定**: `DEBUG`
- **環境變數**: `DJANGO_DEBUG`
- **預設**: `True`（開發環境）
- **生產**: 必須設為 `false`

```bash
DJANGO_DEBUG=false
```

### Secret Key

- **設定**: `SECRET_KEY`
- **環境變數**: `DJANGO_SECRET_KEY`
- **必要**: 是（生產環境）
- **描述**: Django 用於加密簽名的金鑰

```bash
DJANGO_SECRET_KEY=your-secret-key-here
```

⚠️ **切勿將 secret key 提交至版本控制**

### Allowed Hosts

- **設定**: `ALLOWED_HOSTS`
- **環境變數**: `DJANGO_ALLOWED_HOSTS`
- **格式**: 以逗號分隔的主機清單
- **預設**: `*`（僅開發環境）

```bash
DJANGO_ALLOWED_HOSTS=example.com,api.example.com
```

## 資料庫設定

預設使用 PostgreSQL，請透過環境變數設定：

```bash
POSTGRES_DB=app_db
POSTGRES_USER=user
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

**資料庫引擎**: `django.db.backends.postgresql`

## 快取設定

使用 Redis 做為快取與 session 存放：

```bash
REDIS_URL=redis://redis:6379/1
```

**後端**: `django_redis.cache.RedisCache`

## 安全設定

### CORS（跨來源資源分享）

```bash
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

- **設定**: `CORS_ALLOWED_ORIGINS`
- **格式**: 含協定（http:// 或 https://）之逗號分隔 URL 清單
- **注意**: 若缺少協定，系統會自動補上 `http://` 或 `https://`

### CSRF（跨站請求偽造）

```bash
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://app.example.com
```

## 靜態檔案

### Static URL 與 Root

- **STATIC_URL**: `/static/`
- **STATIC_ROOT**: `{BASE_DIR}/staticfiles`
- **STATICFILES_DIRS**: `[{BASE_DIR}/ui/static]`

### WhiteNoise 設定

專案使用 WhiteNoise 以有效率地提供靜態檔案：

- **Storage**: `whitenoise.storage.CompressedManifestStaticFilesStorage`
- **Middleware**: `whitenoise.middleware.WhiteNoiseMiddleware`

### 收集靜態檔案

```bash
python src/manage.py collectstatic --noinput
```

## 日誌設定

日誌設定包含多個 handler 與 formatter：

### 日誌檔

- **一般日誌**: `logs/django.json`（JSON 格式，輪替）
- **Proxy 日誌**: `logs/proxy.json`（JSON 格式，輪替）
- **錯誤日誌**: `logs/django_error.log`（僅 ERROR 等級）
- **除錯日誌**: `logs/django_debug.log`（DEBUG 等級）

### 日誌輪替

- **最大檔案大小**: 每檔 10 MB
- **備份數量**: 3 個檔案
- **Formatter**: JSON（pythonjsonlogger）

### 環境變數

```bash
LOG_JSON_PATH=logs/django.json
PROXY_LOG_JSON_PATH=logs/proxy.json
```

## API 文件設定

### drf-spectacular 設定

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'aivonx proxy API',
    'DESCRIPTION': 'API documentation for aivonx proxy',
    'VERSION': '1.0.0',
}
```

### API 文件 URL

- **OpenAPI Schema**: `/api/schema`
- **Swagger UI**: `/swagger`
- **ReDoc**: `/redoc`

## REST Framework 設定

### 認證

- JWT（SimpleJWT）
- Session Authentication
- Token Authentication

### 權限

**預設**: `IsAuthenticated`（除非明確設為 `AllowAny`，否則所有端點需驗證）

### 分頁

- **Class**: `LimitOffsetPagination`
- **Page Size**: 100 items
- **參數**: `?limit=N&offset=M`

### Schema 產生

**Class**: `drf_spectacular.openapi.AutoSchema`

## 認證相關設定

### Login/Logout URL

- **LOGIN_URL**: `/`
- **LOGIN_REDIRECT_URL**: `/ui/manage`
- **LOGOUT_REDIRECT_URL**: `/`

### 預設 root 密碼

```bash
ROOT_PASSWORD=changeme
```

## 模板設定

模板目錄：
- `{BASE_DIR}/ui/templates`
- `{BASE_DIR}/proxy/templates`
- `{BASE_DIR}/logviewer/templates`

## 國際化

- **Language Code**: `zh-hant`（繁體中文）
- **Time Zone**: `Asia/Taipei`
- **USE_I18N**: `True`
- **USE_TZ**: `True`

## Middleware 清單

1. `django.middleware.security.SecurityMiddleware`
2. `django.contrib.sessions.middleware.SessionMiddleware`
3. `django.middleware.common.CommonMiddleware`
4. `django.middleware.csrf.CsrfViewMiddleware`
5. `django.contrib.auth.middleware.AuthenticationMiddleware`
6. `django.contrib.messages.middleware.MessageMiddleware`
7. `django.middleware.clickjacking.XFrameOptionsMiddleware`
8. `corsheaders.middleware.CorsMiddleware`
9. `whitenoise.middleware.WhiteNoiseMiddleware`

## 已安裝應用

- `django.contrib.admin`
- `django.contrib.auth`
- `django.contrib.contenttypes`
- `django.contrib.sessions`
- `django.contrib.messages`
- `django.contrib.staticfiles`
- `rest_framework`
- `drf_spectacular`
- `corsheaders`
- `proxy` (custom)
- `account` (custom)
- `logviewer` (custom)
