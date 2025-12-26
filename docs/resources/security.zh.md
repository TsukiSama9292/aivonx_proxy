# 安全性指南（繁體中文）

本文檔為 aivonx_proxy 提供完整的安全性建議與設定說明，涵蓋認證、授權、環境變數、CORS/CSRF、資料庫、密碼策略、容器與生產部署檢查表等項目。

## 目錄

- 安全總覽
- 環境設定
- 認證與授權
- CORS 與 CSRF 保護
- 資料庫安全
- 密碼安全
- 生產部署安全檢查表
- 安全中介軟體
- API 端點安全
- 日誌與監控
- 容器安全

## 安全總覽

aivonx_proxy 以多層防護設計來降低常見風險：

- 認證：支援 JWT、Session 與 Token 多種方式
- 授權：使用 DRF 權限類別管理存取控制
- CORS：可設定跨域來源清單
- CSRF：透過 Django 的 CSRF 機制保護狀態變更請求
- 密碼驗證：採用 Django 的密碼驗證器強化密碼安全
- 生產環境預設需明確設定敏感參數

## 環境設定

以下環境變數在生產環境中為必要或強烈建議設定：

### `DJANGO_SECRET_KEY`

關鍵：Django 的 secret key 用於加密簽章，務必保密。

```bash
DJANGO_SECRET_KEY="your-long-random-secret-key-here"
```

建議：
- 在 `DJANGO_DEBUG=false` 時必須設定
- 建議長度 50 字元以上且隨機不可預測
- 切勿將其提交至版本控制系統
- 定期輪換

產生範例：

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### `DJANGO_DEBUG`

控制除錯模式；生產環境務必關閉。

```bash
DJANGO_DEBUG=false
```

影響：
- `true` 時會顯示詳細錯誤與堆疊資訊（不安全）
- `false` 時顯示通用錯誤頁面以保護敏感資訊

接受值：`true`, `false`, `1`, `0`, `yes`, `no`（不區分大小寫）

### `DJANGO_ALLOWED_HOSTS`

以逗號分隔的主機或網域清單，Django 只會回應清單內的 Host 標頭。

```bash
DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com,api.yourdomain.com"
```

注意：在生產環境（`DJANGO_DEBUG=false`）必須設定；開發時使用 `*` 容易造成風險。

### 可選的安全環境變數

`ROOT_PASSWORD`：在初次遷移時建立的管理帳號預設密碼。

```bash
ROOT_PASSWORD="your-secure-password"
```

重要提示：預設值可能為 `changeme`（不安全），上線前務必更改。

## 認證與授權

### 認證方式

應用程式支援三種主要認證方式（見 `src/aivonx/settings.py`）：

1. JWT（使用 `djangorestframework-simplejwt`）
   - 登入端點：`POST /api/account/login`
   - 回傳 `access` 與 `refresh` token，使用 `Authorization: Bearer <token>` 呼叫 API

2. Session（cookie-based）
   - 適用於 Web UI 登入
   - 搭配 CSRF 保護與伺服器端 session（可使用 Redis）

3. Token（DRF Token Authentication）
   - 使用 `Authorization: Token <token>` 的方式

### 預設權限政策

全域預設為必須驗證：

```python
"DEFAULT_PERMISSION_CLASSES": (
    "rest_framework.permissions.IsAuthenticated",
)
```

個別端點可用裝飾器覆寫，常見用法：

- `@permission_classes([IsAuthenticated])`：需要驗證
- `@permission_classes([AllowAny])`：公開（不需驗證）
- `@login_required`：Session 登入保護（Web UI）

注意：某些 proxy 端點（如 `/api/proxy/*`）預設使用 `AllowAny` 以利整合，但生產環境建議採取額外控管（例如 API 金鑰、反向代理限制或僅內網可存取）。

## CORS 與 CSRF 保護

### CORS

使用 `DJANGO_CORS_ALLOWED_ORIGINS` 指定允許的跨域來源（逗號分隔）。

```bash
DJANGO_CORS_ALLOWED_ORIGINS="https://example.com,https://app.example.com"
```

設定會自動補上 `http://`（如未提供 scheme），並支援 `CORS_ALLOW_CREDENTIALS = True`（允許攜帶 cookie），但當啟用此選項時，務必把允許來源限制為可信網域。

### CSRF

使用 `DJANGO_CSRF_TRUSTED_ORIGINS` 指定受信任來源（需包含 scheme）：

```bash
DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://admin.example.com"
```

Django 已啟用 `CsrfViewMiddleware`，且 Web UI 的 POST 操作通常加上 `@csrf_protect` 裝飾器，要求 valid CSRF token。

## 資料庫安全

應用使用 PostgreSQL（環境變數設定）：

```bash
POSTGRES_USER="user"
POSTGRES_PASSWORD="secure-password-here"
POSTGRES_DB="app_db"
POSTGRES_HOST="postgres"
POSTGRES_PORT="5432"
```

建議：

1. 使用強密碼（建議 16 字元以上，混合大小寫、數字與符號）
2. 限制網路存取（透過 `pg_hba.conf` 與防火牆）
3. 在生產環境開啟 SSL/TLS
4. 定期備份並驗證備份可還原
5. 原則上採最小權限帳號

Redis 用於快取與 session：

```bash
REDIS_URL="redis://redis:6379/1"
```

建議：啟用驗證（`requirepass`）、限制綁定位址、分離資料庫索引並停用危險指令

## 密碼安全

Django 已啟用密碼驗證器（UserAttributeSimilarity、MinimumLength、CommonPassword、NumericPassword），並以 PBKDF2-HMAC-SHA256 儲存密碼，會自動在登入時更新較新的雜湊參數。

遷移檔 `src/account/migrations/0003_create_root.py` 會使用 `make_password()` 為 root 帳號雜湊密碼，請勿使用預設弱密碼上線。

## 生產部署安全檢查表

上線前必做：

- [ ] 設定 `DJANGO_DEBUG=false`
- [ ] 設定安全的 `DJANGO_SECRET_KEY`（50+ 字元）
- [ ] 設定 `DJANGO_ALLOWED_HOSTS` 為實際網域
- [ ] 變更 `ROOT_PASSWORD`（勿使用 `changeme`）
- [ ] 強制 HTTPS（TLS）
- [ ] 設定 `DJANGO_CSRF_TRUSTED_ORIGINS`（包含 `https://`）
- [ ] 設定安全的 `POSTGRES_PASSWORD`
- [ ] 檢查並限制 `DJANGO_CORS_ALLOWED_ORIGINS`

建議項目：

- [ ] 啟用資料庫 SSL 連線
- [ ] 為 Redis 設定驗證
- [ ] 建立日誌監控與告警
- [ ] 在認證端點加入速率限制
- [ ] 使用專屬環境檔（勿提交 .env 至 git）
- [ ] 設定自動化備份與還原程序
- [ ] 檢討所有 `AllowAny` 的端點並視情況限制存取

### 建議加入的安全標頭

在生產（HTTPS）環境建議加入：

```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
```

## 安全中介軟體（Middleware）

設定中包含下列中介軟體（見 `src/aivonx/settings.py`）：

`SecurityMiddleware`、`SessionMiddleware`、`CommonMiddleware`、`CsrfViewMiddleware`、`AuthenticationMiddleware`、`MessageMiddleware`、`XFrameOptionsMiddleware`、`corsheaders.middleware.CorsMiddleware`、`whitenoise.middleware.WhiteNoiseMiddleware`。

其用途包括：安全標頭、Session 管理、CSRF 驗證、CORS 檢查、點擊劫持防護與靜態檔案服務。

## API 端點安全

公開端點（`AllowAny`）範例：`/api/account/login`、`/api/proxy/state`、`/api/proxy/generate`、`/api/proxy/chat`、`/api/tags` 等。這些端點有其設計用途，但在需受限的情境下應額外保護（例如反向代理驗證、IP 白名單或在程式中改為 `IsAuthenticated`）。

受保護端點：設定檔與節點管理 API（預設需驗證）、Web UI（`@login_required`）以及 Django admin（只限 staff）。

## 日誌與監控

日誌配置支援 JSON 與 verbose 格式，包含 `logs/django.json`、`logs/django_error.log` 與 `logs/proxy.json`。建議集中化日誌、監控失敗登入、錯誤率、Proxy 使用情形與資料庫行為。

## 容器安全

Docker Compose 範例設定包含 `privileged: false`、`ipc: private` 與健康檢查。建議：

- 以非 root 使用者執行容器
- 使用唯讀檔系統與 tmpfs（視情況）
- 設定資源限制
- 網路分段（前端/後端）並將資料庫放在內部網路
- 使用 secrets 管理敏感資料

也建議定期掃描映像檔漏洞（如 Trivy）與更新基底映像。

## 其他資源

- Django 官方安全與部署檢查表
- OWASP Top 10 與 REST 安全檢核列表
- 建議使用 Bandit、Safety、Trivy 等工具做安全檢測

## 事件通報

發現安全漏洞請勿公開發佈 issue，請直接聯絡維護者並提供重現步驟，保留合理的修補與通報時間。

## 版本記錄

- 2024-12-26：新增完整安全性文件（繁體中文翻譯）
# Security

This document provides comprehensive security guidelines and configuration options for the aivonx_proxy application. It covers authentication, authorization, environment configuration, and best practices for production deployments.

## Table of Contents

- `Security Overview`
- `Environment Configuration`
- `Authentication & Authorization`
- `CORS & CSRF Protection`
- `Database Security`
- `Password Security`
- `Production Security Checklist`
- `Security Middleware`
- `API Endpoint Security`
- `Logging & Monitoring`
- `Container Security`

## Security Overview

The aivonx_proxy application implements multiple layers of security to protect against common vulnerabilities:

- **Authentication**: Multi-method authentication including JWT, Session, and Token authentication
- **Authorization**: Role-based access control with permission classes
- **CORS Protection**: Configurable Cross-Origin Resource Sharing policies
- **CSRF Protection**: Cross-Site Request Forgery protection for state-changing operations
- **Password Validation**: Django's comprehensive password validation framework
- **Secure Defaults**: Production-safe defaults with explicit environment configuration

## Environment Configuration

### Required Environment Variables (Production)

The following environment variables **MUST** be configured in production environments:

#### `DJANGO_SECRET_KEY`

**Critical**: The Django secret key is used for cryptographic signing and MUST be kept secret.

```bash
DJANGO_SECRET_KEY="your-long-random-secret-key-here"
```

**Requirements**:
- Must be set when `DJANGO_DEBUG=false`
- Should be at least 50 characters long
- Must be random and unpredictable
- Never commit to version control
- Rotate periodically in production

**Generation Example**:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### `DJANGO_DEBUG`

Controls Django's debug mode. **MUST be disabled in production**.

```bash
DJANGO_DEBUG=false
```

**Security Impact**:
- When `true`: Exposes detailed error messages, settings, and stack traces
- When `false`: Shows generic error pages, hides sensitive information
- **Always set to `false` in production**

**Accepted Values**: `true`, `false`, `1`, `0`, `yes`, `no` (case-insensitive)

#### `DJANGO_ALLOWED_HOSTS`

Comma-separated list of host/domain names that Django will serve.

```bash
DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com,api.yourdomain.com"
```

**Requirements**:
- Required when `DJANGO_DEBUG=false`
- Must include all domains that will access your application
- Prevents HTTP Host header attacks
- Use `*` only for development (insecure for production)

**Examples**:
```bash
# Production
DJANGO_ALLOWED_HOSTS="example.com,www.example.com"

# Development (NOT for production)
DJANGO_ALLOWED_HOSTS="*"

# IP-based access
DJANGO_ALLOWED_HOSTS="192.168.1.100,10.0.0.50"
```

### Optional Security Environment Variables

#### `ROOT_PASSWORD`

Default password for the root administrative user created during initial migration.

```bash
ROOT_PASSWORD="your-secure-password"
```

**Important**:
- Default value: `changeme` (insecure)
- **MUST be changed before production deployment**
- The root user is created automatically with `username: root`
- Used for administrative access to the web UI and API

**Security Note**: This password is only used during the initial database migration. After deployment, change it immediately through the Django admin interface or command line.

## Authentication & Authorization

### Authentication Methods

The application supports three authentication methods (configured in `../src/aivonx/settings.py#L187-L196`):

#### 1. JWT Authentication (Primary)

JSON Web Token authentication using `djangorestframework-simplejwt`.

**Endpoint**: `POST /api/account/login`

**Request**:
```json
{
  "username": "root",
  "password": "your-password"
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Usage**:
```bash
# Include access token in Authorization header
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Security Features**:
- Stateless authentication
- Time-limited access tokens
- Refresh token rotation support
- No server-side session storage required

#### 2. Session Authentication

Traditional Django session-based authentication using cookies.

**Use Case**: Web UI authentication via login forms

**Login URL**: `/ui/login` (configured via `LOGIN_URL` in `../src/aivonx/settings.py#L176`)

**Features**:
- CSRF protection enabled
- Session cookie security
- Server-side session management via Redis

#### 3. Token Authentication

Django REST Framework token authentication.

**Usage**:
```bash
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### Authorization & Permissions

#### Default Permission Policy

**Global Setting**: All API endpoints require authentication by default.

```python
"DEFAULT_PERMISSION_CLASSES": (
    "rest_framework.permissions.IsAuthenticated",
)
```

#### Permission Decorators

Individual endpoints can override the default policy:

| Decorator | Behavior | Use Case |
|-----------|----------|----------|
| `@permission_classes([IsAuthenticated])` | Requires valid authentication | Protected endpoints |
| `@permission_classes([AllowAny])` | No authentication required | Public endpoints |
| `@login_required` | Requires session login | Web UI views |

#### Endpoint Permission Map

| Endpoint | Permission | Rationale |
|----------|------------|-----------|
| `POST /api/account/login` | `AllowAny` | Public login endpoint |
| `GET /api/proxy/state` | `AllowAny` | Public health/diagnostics |
| `POST /api/proxy/generate` | `AllowAny` | Public proxy endpoint (configurable) |
| `POST /api/proxy/chat` | `AllowAny` | Public proxy endpoint (configurable) |
| `POST /api/proxy/embeddings` | `AllowAny` | Public proxy endpoint (configurable) |
| `GET /api/tags` | `AllowAny` | Public model discovery |
| `GET /api/config` | `IsAuthenticated` | Protected configuration access |
| Web UI (`/ui/manage`) | `@login_required` | Session-based authentication |
| Admin Panel (`/admin/`) | Staff users only | Django built-in admin |

**Security Consideration**: The proxy endpoints (`/api/proxy/*`) use `AllowAny` by default to facilitate integration with external tools. For production deployments requiring access control, consider:
1. Implementing API key authentication
2. Using a reverse proxy (nginx, Traefik) for IP whitelisting
3. Deploying within a private network/VPN

### Web UI Authentication

Web-based management interface requires session authentication:

- **Login URL**: `/ui/login`
- **Protected URL**: `/ui/manage`
- **Logout URL**: `/logout`
- **Decorator**: `@login_required` + `@csrf_protect`

**Features**:
- Session-based authentication with Redis backend
- CSRF protection on all POST requests
- Automatic redirect to login page for unauthenticated users
- Redirect to management page after successful login

## CORS & CSRF Protection

### CORS (Cross-Origin Resource Sharing)

#### `DJANGO_CORS_ALLOWED_ORIGINS`

Comma-separated list of origins allowed to make cross-origin requests.

```bash
DJANGO_CORS_ALLOWED_ORIGINS="https://example.com,https://app.example.com"
```

**Configuration**:
- Automatically prefixes `http://` if scheme is missing
- Supports both HTTP and HTTPS origins
- Empty by default (no origins allowed)
- Required for browser-based clients on different domains

**Examples**:
```bash
# Multiple origins with explicit schemes
DJANGO_CORS_ALLOWED_ORIGINS="https://example.com,https://api.example.com"

# Will be auto-prefixed with http://
DJANGO_CORS_ALLOWED_ORIGINS="localhost:3000,192.168.1.100:8080"

# Production with multiple frontend domains
DJANGO_CORS_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com,https://mobile.example.com"
```

#### CORS Settings

```python
CORS_ALLOW_CREDENTIALS = True  # Allow cookies in cross-origin requests
```

**Security Note**: Only enable `CORS_ALLOW_CREDENTIALS` if your frontend needs to send cookies or authentication headers. Always pair with a restrictive `DJANGO_CORS_ALLOWED_ORIGINS` list.

### CSRF (Cross-Site Request Forgery)

#### `DJANGO_CSRF_TRUSTED_ORIGINS`

List of origins trusted for CSRF-protected requests (especially POST, PUT, DELETE).

```bash
DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://admin.example.com"
```

**Requirements**:
- Must include scheme (`http://` or `https://`)
- Required for any domain making POST/PUT/DELETE requests
- Automatically prefixes `http://` if scheme is missing
- Must match the domains users will access

**Examples**:
```bash
# Production HTTPS deployment
DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://www.example.com"

# Development environment
DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

# Mixed environments (not recommended)
DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:8000,https://production.example.com"
```

#### CSRF Middleware

CSRF protection is enforced via Django's `CsrfViewMiddleware`:

```python
MIDDLEWARE = [
    ...
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]
```

**Protected Views**: All web UI views with `@csrf_protect` decorator require valid CSRF tokens in POST requests.

## Database Security

### PostgreSQL Configuration

The application uses PostgreSQL as the primary database. Credentials are configured via environment variables:

```bash
POSTGRES_USER="user"
POSTGRES_PASSWORD="secure-password-here"
POSTGRES_DB="app_db"
POSTGRES_HOST="postgres"
POSTGRES_PORT="5432"
```

**Security Recommendations**:
1. **Use strong passwords**: Minimum 16 characters with mixed case, numbers, and symbols
2. **Limit network access**: Configure `pg_hba.conf` to restrict connections
3. **Use SSL/TLS**: Enable SSL connections in production
4. **Regular backups**: Implement automated backup procedures
5. **Least privilege**: Create application-specific database users with minimal permissions

### Redis Configuration

Redis is used for caching and session storage:

```bash
REDIS_URL="redis://redis:6379/1"
```

**Security Recommendations**:
1. **Enable authentication**: Set `requirepass` in redis.conf
2. **Bind to localhost**: Prevent external access unless required
3. **Use separate databases**: Isolate cache and session data
4. **Disable dangerous commands**: Use `rename-command` for FLUSHDB, FLUSHALL, etc.

### Connection Security

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("POSTGRES_DB", "app_db"),
        'USER': os.getenv("POSTGRES_USER", "user"),
        'PASSWORD': os.getenv("POSTGRES_PASSWORD", "password"),
        'HOST': os.getenv("POSTGRES_HOST", "postgres"),
        'PORT': os.getenv("POSTGRES_PORT", "5432"),
    }
}
```

**Production Hardening**:
- Enable SSL: Add `'OPTIONS': {'sslmode': 'require'}` to the database configuration
- Use connection pooling
- Set appropriate connection timeouts
- Monitor database logs for suspicious activity

## Password Security

### Password Validation

Django enforces strong password requirements through validators:

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        # Prevents passwords similar to user attributes (username, email, etc.)
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        # Default: Minimum 8 characters
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        # Prevents use of common passwords (top 20,000 most common)
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        # Prevents entirely numeric passwords
    },
]
```

**Enforced Requirements**:
- ✓ Minimum 8 characters (configurable)
- ✓ Cannot be entirely numeric
- ✓ Cannot be too similar to username or email
- ✓ Cannot be a commonly used password
- ✓ Validated on user creation and password changes

### Password Hashing

Django uses PBKDF2 algorithm with SHA256 hash for password storage:

- **Algorithm**: PBKDF2-HMAC-SHA256
- **Iterations**: 870,000 (Django 5.2 default, increases with each version)
- **Automatic upgrading**: Passwords are rehashed on login if iteration count increases

**Security Note**: Passwords are never stored in plain text. The migration `../src/account/migrations/0003_create_root.py` uses `make_password()` to hash the root password before storage.

## Production Security Checklist

Use this checklist before deploying to production:

### Critical (Must-Have)

- [ ] Set `DJANGO_DEBUG=false`
- [ ] Configure `DJANGO_SECRET_KEY` with a strong, random value (50+ characters)
- [ ] Set `DJANGO_ALLOWED_HOSTS` to your actual domain(s)
- [ ] Change `ROOT_PASSWORD` from default `changeme`
- [ ] Enable HTTPS/TLS for all connections
- [ ] Configure `DJANGO_CSRF_TRUSTED_ORIGINS` with your domains (including `https://` scheme)
- [ ] Set strong `POSTGRES_PASSWORD` (16+ characters)
- [ ] Review and restrict `DJANGO_CORS_ALLOWED_ORIGINS`

### Recommended

- [ ] Enable database SSL connections
- [ ] Configure Redis authentication (`requirepass`)
- [ ] Set up log monitoring and alerting
- [ ] Implement rate limiting on authentication endpoints
- [ ] Use environment-specific `.env` files (never commit to git)
- [ ] Enable Redis persistence for session data
- [ ] Configure firewall rules to restrict database access
- [ ] Set up automated database backups
- [ ] Review all `AllowAny` permission endpoints and restrict if necessary
- [ ] Implement API key authentication for proxy endpoints if needed

### Security Headers (Recommended Additions)

Consider adding these security middleware and headers:

```python
# settings.py additions for production

# Security Middleware Settings
SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
SESSION_COOKIE_SECURE = True  # HTTPS only cookies
CSRF_COOKIE_SECURE = True  # HTTPS only CSRF cookies
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
CSRF_COOKIE_HTTPONLY = True
```

**Note**: These settings are not currently enabled by default but are strongly recommended for production HTTPS deployments.

## Security Middleware

The application uses Django's security middleware stack (configured in `../src/aivonx/settings.py#L68-L77`):

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Security headers
    'django.contrib.sessions.middleware.SessionMiddleware',  # Session management
    'django.middleware.common.CommonMiddleware',  # Common utilities
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Auth
    'django.contrib.messages.middleware.MessageMiddleware',  # Flash messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking protection
    'corsheaders.middleware.CorsMiddleware',  # CORS handling
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving
]
```

### Middleware Functions

| Middleware | Function | Security Benefit |
|------------|----------|------------------|
| `SecurityMiddleware` | Adds security headers | HSTS, SSL redirect, content type sniffing protection |
| `SessionMiddleware` | Manages user sessions | Secure session handling via Redis |
| `CsrfViewMiddleware` | CSRF token validation | Prevents CSRF attacks on state-changing operations |
| `AuthenticationMiddleware` | User authentication | Attaches authenticated user to requests |
| `XFrameOptionsMiddleware` | X-Frame-Options header | Prevents clickjacking attacks |
| `CorsMiddleware` | CORS policy enforcement | Controls cross-origin resource access |

## API Endpoint Security

### Public Endpoints (No Authentication Required)

These endpoints use `@permission_classes([AllowAny])`:

| Endpoint | Method | Purpose | Security Note |
|----------|--------|---------|---------------|
| `/api/account/login` | POST | User authentication | Public by design (login endpoint) |
| `/api/proxy/state` | GET | Health check | Diagnostics endpoint, minimal information exposure |
| `/api/proxy/generate` | POST | Ollama proxy | Consider restricting in production |
| `/api/proxy/chat` | POST | Ollama proxy | Consider restricting in production |
| `/api/proxy/embeddings` | POST | Ollama proxy | Consider restricting in production |
| `/api/proxy/embed` | POST | Ollama proxy | Consider restricting in production |
| `/api/tags` | GET | Model listing | Public model discovery |
| `/health` | GET | Application health | Basic health check |

### Protected Endpoints (Authentication Required)

These endpoints require valid authentication (JWT, Session, or Token):

| Endpoint | Method | Permission | Purpose |
|----------|--------|------------|---------|
| `/api/config` | GET | `IsAuthenticated` | Configuration retrieval |
| `/api/proxy/nodes` | GET/POST/PUT/DELETE | Default (`IsAuthenticated`) | Node management |
| `/ui/manage` | GET/POST | `@login_required` | Web UI management interface |
| `/admin/*` | ALL | Staff users | Django admin panel |

### Security Recommendations for Proxy Endpoints

The proxy endpoints (`/api/proxy/*`) are public by default to facilitate integration with Ollama-compatible tools. For production deployments requiring access control:

#### Option 1: Reverse Proxy Authentication

Use nginx or Traefik to add authentication:

```nginx
location /api/proxy/ {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://django:8000;
}
```

#### Option 2: IP Whitelisting

Restrict access to known IP addresses:

```nginx
location /api/proxy/ {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://django:8000;
}
```

#### Option 3: VPN/Private Network

Deploy within a private network accessible only via VPN.

#### Option 4: Custom Authentication

Modify the code to require authentication:

```python
# In views_proxy.py, change:
@permission_classes([AllowAny])
# To:
@permission_classes([IsAuthenticated])
```

## Logging & Monitoring

### Security-Relevant Logging

The application implements comprehensive logging (configured in `../src/aivonx/settings.py#L214-L326`):

#### Log Files

| Log File | Purpose | Content |
|----------|---------|---------|
| `logs/django.json` | General application logs | INFO level, all Django operations |
| `logs/django_error.log` | Error logs | ERROR level, exceptions and errors |
| `logs/proxy.json` | Proxy operation logs | Proxy requests, node selection, errors |

#### Security Events Logged

- Authentication attempts (success/failure)
- Authorization failures
- Request errors (400, 401, 403, 404, 500 series)
- Database connection issues
- Proxy node failures

#### Log Formats

- **JSON Format**: Structured logs for easy parsing and analysis
- **Verbose Format**: Detailed logs with module, process, thread information
- **Rotation**: 10MB per file, 3 backups retained

### Monitoring Recommendations

1. **Monitor failed authentication attempts**: Detect brute-force attacks
2. **Track error rates**: Identify potential attacks or system issues
3. **Monitor proxy endpoint usage**: Detect abuse or unusual patterns
4. **Database connection monitoring**: Detect potential database attacks
5. **Log aggregation**: Use ELK stack, Splunk, or similar for centralized logging

### Example: Monitoring Failed Logins

```bash
# Parse JSON logs for failed login attempts
cat logs/django.json | jq 'select(.message | contains("Invalid credentials"))'

# Count failed login attempts in the last hour
cat logs/django.json | \
  jq -r 'select(.message | contains("Invalid credentials")) | .asctime' | \
  awk -v now="$(date +%s)" '{ ... }' | wc -l
```

## Container Security

### Docker Configuration

The application runs in Docker containers with security configurations:

#### Container Settings (`../docker-compose.yml#L1-L8`)

```yaml
x-default-opts: &default-opts
  restart: unless-stopped
  tty: true
  stdin_open: true
  privileged: false  # Never run with elevated privileges
  ipc: private  # Isolated IPC namespace
```

**Security Features**:
- ✓ `privileged: false` - Prevents container from gaining root-equivalent host access
- ✓ `ipc: private` - Isolates inter-process communication
- ✓ Non-root user context (recommended addition, see below)
- ✓ Health checks for all services
- ✓ Isolated bridge network

### Container Hardening Recommendations

#### 1. Run as Non-Root User

Add to Dockerfile:

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

#### 2. Read-Only Filesystem

```yaml
services:
  django:
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
```

#### 3. Resource Limits

```yaml
services:
  django:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M
```

#### 4. Network Segmentation

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No internet access

services:
  django:
    networks:
      - frontend
      - backend
  postgres:
    networks:
      - backend  # Database only accessible from backend network
```

#### 5. Secrets Management

Use Docker secrets instead of environment variables for sensitive data:

```yaml
secrets:
  db_password:
    external: true
  secret_key:
    external: true

services:
  django:
    secrets:
      - db_password
      - secret_key
```

### Image Security

- **Base Image**: `python:3.12-slim-bookworm` (minimal attack surface)
- **Package Updates**: Regular base image updates
- **Vulnerability Scanning**: Run `docker scan` or Trivy regularly

```bash
# Scan for vulnerabilities
docker scan aivonx_proxy:latest

# Or use Trivy
trivy image aivonx_proxy:latest
```

## Additional Security Resources

### Django Security Documentation

- [Django Security Overview](https://docs.djangoproject.com/en/5.2/topics/security/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django Authentication System](https://docs.djangoproject.com/en/5.2/topics/auth/)

### OWASP Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

### Security Testing Tools

- **OWASP ZAP**: Automated security testing
- **Bandit**: Python security linter
- **Safety**: Python dependency vulnerability scanner
- **Trivy**: Container vulnerability scanner

```bash
# Run security checks
bandit -r src/
safety check
trivy image your-image:tag
```

## Security Contact

If you discover a security vulnerability, please:

1. **Do NOT** open a public issue
2. Email the maintainers directly (see `../../README.md`)
3. Include detailed steps to reproduce
4. Allow reasonable time for a fix before public disclosure

## Changelog

- **2024-12-26**: Initial comprehensive security documentation
- Added detailed environment variable descriptions
- Added authentication and authorization sections
- Added production security checklist
- Added container security recommendations
