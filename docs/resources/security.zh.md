# 安全性

本文件提供 aivonx_proxy 應用程式的全面安全性指南和配置選項。它涵蓋認證、授權、環境配置以及生產部署的最佳實踐。

## 目錄

- `安全性概述`
- `環境配置`
- `認證與授權`
- `CORS 與 CSRF 保護`
- `資料庫安全性`
- `密碼安全性`
- `生產安全性檢查清單`
- `安全性中介軟體`
- `API 端點安全性`
- `日誌與監控`
- `容器安全性`

## 安全性概述

aivonx_proxy 應用程式實作多層安全性來保護常見漏洞：

- **認證**：多方法認證，包括 JWT、Session 和 Token 認證
- **授權**：基於角色的存取控制與權限類別
- **CORS 保護**：可配置的跨來源資源共享政策
- **CSRF 保護**：針對狀態變更操作的跨站請求偽造保護
- **密碼驗證**：Django 的全面密碼驗證框架
- **安全預設**：生產安全的預設值與明確的環境配置

## 環境配置

### 必需的環境變數（生產環境）

以下環境變數**必須**在生產環境中配置：

#### `DJANGO_SECRET_KEY`

**關鍵**：Django 秘密金鑰用於密碼學簽署，**必須**保密。

```bash
DJANGO_SECRET_KEY="your-long-random-secret-key-here"
```

**要求**：
- 當 `DJANGO_DEBUG=false` 時必須設定
- 應至少 50 個字元長
- 必須隨機且不可預測
- 永遠不要提交到版本控制
- 在生產中定期輪換

**生成範例**：
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### `DJANGO_DEBUG`

控制 Django 的除錯模式。**必須**在生產中停用。

```bash
DJANGO_DEBUG=false
```

**安全性影響**：
- 當 `true`：暴露詳細的錯誤訊息、設定和堆疊追蹤
- 當 `false`：顯示通用錯誤頁面，隱藏敏感資訊
- **總是在生產中設定為 `false`**

**接受值**：`true`、`false`、`1`、`0`、`yes`、`no`（不區分大小寫）

#### `DJANGO_ALLOWED_HOSTS`

Django 將服務的以逗號分隔的主機/域名列表。

```bash
DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com,api.yourdomain.com"
```

**要求**：
- 當 `DJANGO_DEBUG=false` 時必需
- 必須包含所有將存取您應用程式的域名
- 防止 HTTP Host 標頭攻擊
- 僅在開發中使用 `*`（生產中不安全）

**範例**：
```bash
# 生產
DJANGO_ALLOWED_HOSTS="example.com,www.example.com"

# 開發（非生產）
DJANGO_ALLOWED_HOSTS="*"

# 基於 IP 的存取
DJANGO_ALLOWED_HOSTS="192.168.1.100,10.0.0.50"
```

### 可選的安全性環境變數

#### `ROOT_PASSWORD`

初始遷移期間建立的根管理使用者的預設密碼。

```bash
ROOT_PASSWORD="your-secure-password"
```

**重要**：
- 預設值：`changeme`（不安全）
- **必須在生產部署前變更**
- 根使用者自動建立，使用者名稱為 `root`
- 用於網頁 UI 和 API 的管理存取

**安全性注意**：此密碼僅在初始資料庫遷移期間使用。部署後，立即透過 Django 管理介面或命令列變更它。

## 認證與授權

### 認證方法

應用程式支援三種認證方法（在 `../src/aivonx/settings.py#L187-L196` 中配置）：

#### 1. JWT 認證（主要）

使用 `djangorestframework-simplejwt` 的 JSON Web Token 認證。

**端點**：`POST /api/account/login`

**請求**：
```json
{
  "username": "root",
  "password": "your-password"
}
```

**回應**：
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**使用**：
```bash
# 在 Authorization 標頭中包含存取權杖
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**安全性功能**：
- 無狀態認證
- 有時間限制的存取權杖
- 支援重新整理權杖輪換
- 不需要伺服器端會話儲存

#### 2. Session 認證

使用 cookie 的傳統 Django 會話式認證。

**使用案例**：透過登入表單的網頁 UI 認證

**登入 URL**：`/ui/login`（透過 `../src/aivonx/settings.py#L176` 中的 `LOGIN_URL` 配置）

**功能**：
- 啟用 CSRF 保護
- 會話 cookie 安全性
- 透過 Redis 的伺服器端會話管理

#### 3. Token 認證

Django REST Framework token 認證。

**使用**：
```bash
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### 授權與權限

#### 預設權限政策

**全域設定**：所有 API 端點預設需要認證。

```python
"DEFAULT_PERMISSION_CLASSES": (
    "rest_framework.permissions.IsAuthenticated",
)
```

#### 權限裝飾器

個別端點可以覆寫預設政策：

| 裝飾器 | 行為 | 使用案例 |
|-----------|----------|----------|
| `@permission_classes([IsAuthenticated])` | 需要有效認證 | 受保護端點 |
| `@permission_classes([AllowAny])` | 不需要認證 | 公開端點 |
| `@login_required` | 需要會話登入 | 網頁 UI 檢視 |

#### 端點權限對應

| 端點 | 權限 | 理由 |
|----------|------------|-----------|
| `POST /api/account/login` | `AllowAny` | 公開登入端點 |
| `GET /api/proxy/state` | `AllowAny` | 公開健康/診斷 |
| `POST /api/proxy/generate` | `AllowAny` | 公開代理端點（可配置） |
| `POST /api/proxy/chat` | `AllowAny` | 公開代理端點（可配置） |
| `POST /api/proxy/embeddings` | `AllowAny` | 公開代理端點（可配置） |
| `GET /api/tags` | `AllowAny` | 公開模型發現 |
| `GET /api/config` | `IsAuthenticated` | 受保護配置存取 |
| 網頁 UI (`/ui/manage`) | `@login_required` | 會話式認證 |
| 管理面板 (`/admin/`) | 僅限員工使用者 | Django 內建管理 |

**安全性考量**：代理端點（`/api/proxy/*`）預設使用 `AllowAny` 以便與外部工具整合。對於需要存取控制的生產部署，請考慮：
1. 實作 API 金鑰認證
2. 使用反向代理（nginx、Traefik）進行 IP 白名單
3. 在私有網路/VPN 中部署

### 網頁 UI 認證

網頁式管理介面需要會話認證：

- **登入 URL**：`/ui/login`
- **受保護 URL**：`/ui/manage`
- **登出 URL**：`/logout`
- **裝飾器**：`@login_required` + `@csrf_protect`

**功能**：
- 使用 Redis 後端的會話式認證
- 在所有 POST 請求上啟用 CSRF 保護
- 未認證使用者自動重新導向至登入頁面
- 成功登入後重新導向至管理頁面

## CORS 與 CSRF 保護

### CORS（跨來源資源共享）

#### `DJANGO_CORS_ALLOWED_ORIGINS`

允許進行跨來源請求的來源以逗號分隔列表。

```bash
DJANGO_CORS_ALLOWED_ORIGINS="https://example.com,https://app.example.com"
```

**配置**：
- 如果缺少方案，自動加上 `http://`
- 支援 HTTP 和 HTTPS 來源
- 預設為空（不允許任何來源）
- 對於不同域名的瀏覽器式客戶端必需

**範例**：
```bash
# 多個來源與明確方案
DJANGO_CORS_ALLOWED_ORIGINS="https://example.com,https://api.example.com"

# 將自動加上 http://
DJANGO_CORS_ALLOWED_ORIGINS="localhost:3000,192.168.1.100:8080"

# 多個前端域名的生產
DJANGO_CORS_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com,https://mobile.example.com"
```

#### CORS 設定

```python
CORS_ALLOW_CREDENTIALS = True  # 允許跨來源請求中的 cookie
```

**安全性注意**：僅在您的前端需要傳送 cookie 或認證標頭時啟用 `CORS_ALLOW_CREDENTIALS`。總是與限制性的 `DJANGO_CORS_ALLOWED_ORIGINS` 列表配對。

### CSRF（跨站請求偽造）

#### `DJANGO_CSRF_TRUSTED_ORIGINS`

受信任的來源列表，用於 CSRF 保護請求（特別是 POST、PUT、DELETE）。

```bash
DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://admin.example.com"
```

**要求**：
- 必須包含方案（`http://` 或 `https://`）
- 對於任何進行 POST/PUT/DELETE 請求的域名必需
- 如果缺少方案，自動加上 `http://`
- 必須匹配使用者將存取的域名

**範例**：
```bash
# HTTPS 生產部署
DJANGO_CSRF_TRUSTED_ORIGINS="https://example.com,https://www.example.com"

# 開發環境
DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

# 混合環境（不推薦）
DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:8000,https://production.example.com"
```

#### CSRF 中介軟體

CSRF 保護透過 Django 的 `CsrfViewMiddleware` 強制執行：

```python
MIDDLEWARE = [
    ...
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]
```

**受保護檢視**：所有帶有 `@csrf_protect` 裝飾器的網頁 UI 檢視在 POST 請求中需要有效的 CSRF 權杖。

## 資料庫安全性

### PostgreSQL 配置

應用程式使用 PostgreSQL 作為主要資料庫。憑證透過環境變數配置：

```bash
POSTGRES_USER="user"
POSTGRES_PASSWORD="secure-password-here"
POSTGRES_DB="app_db"
POSTGRES_HOST="postgres"
POSTGRES_PORT="5432"
```

**安全性建議**：
1. **使用強密碼**：至少 16 個字元，包含大小寫、數字和符號
2. **限制網路存取**：配置 `pg_hba.conf` 以限制連線
3. **使用 SSL/TLS**：在生產中啟用 SSL 連線
4. **定期備份**：實作自動化備份程序
5. **最小權限**：建立應用程式特定的資料庫使用者，具有最小權限

### Redis 配置

Redis 用於快取和會話儲存：

```bash
REDIS_URL="redis://redis:6379/1"
```

**安全性建議**：
1. **啟用認證**：在 redis.conf 中設定 `requirepass`
2. **綁定到 localhost**：除非必需，否則防止外部存取
3. **使用單獨資料庫**：隔離快取和會話資料
4. **停用危險命令**：對 FLUSHDB、FLUSHALL 等使用 `rename-command`

### 連線安全性

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

**生產強化**：
- 啟用 SSL：將 `'OPTIONS': {'sslmode': 'require'}` 新增到資料庫配置
- 使用連線池
- 設定適當的連線逾時
- 監控資料庫日誌以發現可疑活動

## 密碼安全性

### 密碼驗證

Django 透過驗證器強制強密碼要求：

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        # 防止密碼類似使用者屬性（使用者名稱、電子郵件等）
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        # 預設：至少 8 個字元
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        # 防止使用常見密碼（前 20,000 個最常見）
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        # 防止完全數值的密碼
    },
]
```

**強制要求**：
- ✓ 至少 8 個字元（可配置）
- ✓ 不能完全數值
- ✓ 不能太類似使用者名稱或電子郵件
- ✓ 不能是常用密碼
- ✓ 在使用者建立和密碼變更時驗證

### 密碼雜湊

Django 使用 PBKDF2 演算法與 SHA256 雜湊進行密碼儲存：

- **演算法**：PBKDF2-HMAC-SHA256
- **迭代**：870,000（Django 5.2 預設，每個版本增加）
- **自動升級**：如果迭代計數增加，密碼在登入時重新雜湊

**安全性注意**：密碼永遠不會以明文儲存。遷移 `../src/account/migrations/0003_create_root.py` 使用 `make_password()` 在儲存前雜湊根密碼。

## 生產安全性檢查清單

在部署到生產前使用此檢查清單：

### 關鍵（必須有）

- [ ] 設定 `DJANGO_DEBUG=false`
- [ ] 使用強隨機值（50+ 字元）配置 `DJANGO_SECRET_KEY`
- [ ] 將 `DJANGO_ALLOWED_HOSTS` 設定為您的實際域名
- [ ] 從預設 `changeme` 變更 `ROOT_PASSWORD`
- [ ] 為所有連線啟用 HTTPS/TLS
- [ ] 使用您的域名（包括 `https://` 方案）配置 `DJANGO_CSRF_TRUSTED_ORIGINS`
- [ ] 設定強 `POSTGRES_PASSWORD`（16+ 字元）
- [ ] 檢視並限制 `DJANGO_CORS_ALLOWED_ORIGINS`

### 推薦

- [ ] 啟用資料庫 SSL 連線
- [ ] 配置 Redis 認證（`requirepass`）
- [ ] 設定日誌監控和警報
- [ ] 在認證端點上實作速率限制
- [ ] 使用環境特定的 `.env` 檔案（永遠不要提交到 git）
- [ ] 啟用 Redis 持久性以進行會話資料
- [ ] 配置防火牆規則以限制資料庫存取
- [ ] 設定自動化資料庫備份
- [ ] 檢視所有 `AllowAny` 權限端點並視需要限制
- [ ] 為代理端點實作 API 金鑰認證（如需要）

### 安全性標頭（推薦新增）

考慮新增這些安全性中介軟體和標頭：

```python
# settings.py 新增以進行生產

# 安全性中介軟體設定
SECURE_SSL_REDIRECT = True  # 將 HTTP 重新導向至 HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'  # 防止點擊劫持
SESSION_COOKIE_SECURE = True  # HTTPS 僅 cookie
CSRF_COOKIE_SECURE = True  # HTTPS 僅 CSRF cookie
SESSION_COOKIE_HTTPONLY = True  # 防止 JavaScript 存取會話 cookie
CSRF_COOKIE_HTTPONLY = True
```

**注意**：這些設定預設未啟用，但強烈推薦用於 HTTPS 生產部署。

## 安全性中介軟體

應用程式使用 Django 的安全性中介軟體堆疊（在 `../src/aivonx/settings.py#L68-L77` 中配置）：

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # 安全性標頭
    'django.contrib.sessions.middleware.SessionMiddleware',  # 會話管理
    'django.middleware.common.CommonMiddleware',  # 通用工具
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF 保護
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # 認證
    'django.contrib.messages.middleware.MessageMiddleware',  # 快閃訊息
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # 點擊劫持保護
    'corsheaders.middleware.CorsMiddleware',  # CORS 處理
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 靜態檔案服務
]
```

### 中介軟體功能

| 中介軟體 | 功能 | 安全性益處 |
|------------|----------|------------------|
| `SecurityMiddleware` | 新增安全性標頭 | HSTS、SSL 重新導向、內容類型嗅探保護 |
| `SessionMiddleware` | 管理使用者會話 | 透過 Redis 的安全會話處理 |
| `CsrfViewMiddleware` | CSRF 權杖驗證 | 防止 CSRF 攻擊於狀態變更操作 |
| `AuthenticationMiddleware` | 使用者認證 | 將認證使用者附加到請求 |
| `XFrameOptionsMiddleware` | X-Frame-Options 標頭 | 防止點擊劫持攻擊 |
| `CorsMiddleware` | CORS 政策強制 | 控制跨來源資源存取 |

## API 端點安全性

### 公開端點（不需要認證）

這些端點使用 `@permission_classes([AllowAny])`：

| 端點 | 方法 | 目的 | 安全性注意 |
|----------|--------|---------|---------------|
| `/api/account/login` | POST | 使用者認證 | 設計為公開（登入端點） |
| `/api/proxy/state` | GET | 健康檢查 | 診斷端點，最小資訊暴露 |
| `/api/proxy/generate` | POST | Ollama 代理 | 考慮在生產中限制 |
| `/api/proxy/chat` | POST | Ollama 代理 | 考慮在生產中限制 |
| `/api/proxy/embeddings` | POST | Ollama 代理 | 考慮在生產中限制 |
| `/api/proxy/embed` | POST | Ollama 代理 | 考慮在生產中限制 |
| `/api/tags` | GET | 模型列表 | 公開模型發現 |
| `/health` | GET | 應用程式健康 | 基本健康檢查 |

### 受保護端點（需要認證）

這些端點需要有效認證（JWT、Session 或 Token）：

| 端點 | 方法 | 權限 | 目的 |
|----------|--------|------------|---------|
| `/api/config` | GET | `IsAuthenticated` | 配置擷取 |
| `/api/proxy/nodes` | GET/POST/PUT/DELETE | 預設（`IsAuthenticated`） | 節點管理 |
| `/ui/manage` | GET/POST | `@login_required` | 網頁 UI 管理介面 |
| `/admin/*` | ALL | 員工使用者 | Django 管理面板 |

### 代理端點的安全性建議

代理端點（`/api/proxy/*`）預設為公開以便與 Ollama 相容工具整合。對於需要存取控制的生產部署：

#### 選項 1：反向代理認證

使用 nginx 或 Traefik 新增認證：

```nginx
location /api/proxy/ {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://django:8000;
}
```

#### 選項 2：IP 白名單

限制存取已知 IP 位址：

```nginx
location /api/proxy/ {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://django:8000;
}
```

#### 選項 3：VPN/私有網路

在僅透過 VPN 存取的私有網路中部署。

#### 選項 4：自訂認證

修改程式碼以需要認證：

```python
# 在 views_proxy.py 中，變更：
@permission_classes([AllowAny])
# 為：
@permission_classes([IsAuthenticated])
```

## 日誌與監控

### 安全性相關日誌

應用程式實作全面日誌（在 `../src/aivonx/settings.py#L214-L326` 中配置）：

#### 日誌檔案

| 日誌檔案 | 目的 | 內容 |
|----------|---------|---------|
| `logs/django.json` | 一般應用程式日誌 | INFO 級別，所有 Django 操作 |
| `logs/django_error.log` | 錯誤日誌 | ERROR 級別，例外和錯誤 |
| `logs/proxy.json` | 代理操作日誌 | 代理請求、節點選擇、錯誤 |

#### 記錄的安全性事件

- 認證嘗試（成功/失敗）
- 授權失敗
- 請求錯誤（400、401、403、404、500 系列）
- 資料庫連線問題
- 代理節點失敗

#### 日誌格式

- **JSON 格式**：結構化日誌，便於解析和分析
- **詳細格式**：詳細日誌，具有模組、處理序、執行緒資訊
- **輪換**：每個檔案 10MB，保留 3 個備份

### 監控建議

1. **監控失敗認證嘗試**：偵測暴力攻擊
2. **追蹤錯誤率**：識別潛在攻擊或系統問題
3. **監控代理端點使用**：偵測濫用或異常模式
4. **資料庫連線監控**：偵測潛在資料庫攻擊
5. **日誌聚合**：使用 ELK 堆疊、Splunk 或類似進行集中式日誌

### 範例：監控失敗登入

```bash
# 解析 JSON 日誌以尋找失敗登入嘗試
cat logs/django.json | jq 'select(.message | contains("Invalid credentials"))'

# 計算過去一小時的失敗登入嘗試數
cat logs/django.json | \
  jq -r 'select(.message | contains("Invalid credentials")) | .asctime' | \
  awk -v now="$(date +%s)" '{ ... }' | wc -l
```

## 容器安全性

### Docker 配置

應用程式在具有安全性配置的 Docker 容器中執行：

#### 容器設定（`../docker-compose.yml#L1-L8`）

```yaml
x-default-opts: &default-opts
  restart: unless-stopped
  tty: true
  stdin_open: true
  privileged: false  # 永遠不要以提升權限執行
  ipc: private  # 隔離 IPC 命名空間
```

**安全性功能**：
- ✓ `privileged: false` - 防止容器獲得根等效主機存取
- ✓ `ipc: private` - 隔離處理序間通訊
- ✓ 非根使用者上下文（推薦新增，請參見下方）
- ✓ 所有服務的健康檢查
- ✓ 隔離橋接網路

### 容器強化建議

#### 1. 以非根使用者執行

新增到 Dockerfile：

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

#### 2. 唯讀檔案系統

```yaml
services:
  django:
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
```

#### 3. 資源限制

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

#### 4. 網路分段

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 無網際網路存取

services:
  django:
    networks:
      - frontend
      - backend
  postgres:
    networks:
      - backend  # 資料庫僅從後端網路存取
```

#### 5. 秘密管理

使用 Docker 秘密而非環境變數進行敏感資料：

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

### 映像安全性

- **基礎映像**：`python:3.12-slim-bookworm`（最小攻擊面）
- **套件更新**：定期基礎映像更新
- **漏洞掃描**：定期執行 `docker scan` 或 Trivy

```bash
# 掃描漏洞
docker scan aivonx_proxy:latest

# 或使用 Trivy
trivy image aivonx_proxy:latest
```

## 額外安全性資源

### Django 安全性文件

- [Django 安全性概述](https://docs.djangoproject.com/en/5.2/topics/security/)
- [Django 部署檢查清單](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django 認證系統](https://docs.djangoproject.com/en/5.2/topics/auth/)

### OWASP 資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP REST 安全性速查表](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [OWASP Docker 安全性速查表](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

### 安全性測試工具

- **OWASP ZAP**：自動化安全性測試
- **Bandit**：Python 安全性 linter
- **Safety**：Python 依賴漏洞掃描器
- **Trivy**：容器漏洞掃描器

```bash
# 執行安全性檢查
bandit -r src/
safety check
trivy image your-image:tag
```

## 安全性聯絡

如果您發現安全性漏洞，請：

1. **不要**開啟公開問題
2. 直接電子郵件維護者（請參見 `../../README.md`）
3. 包含重現的詳細步驟
4. 在公開披露前允許合理時間修復