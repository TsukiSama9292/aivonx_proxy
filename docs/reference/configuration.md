# Configuration Reference

The main configuration file is located at `src/aivonx/settings.py`.

## Core Settings

### Debug Mode

- **Setting**: `DEBUG`
- **Environment Variable**: `DJANGO_DEBUG`
- **Default**: `True` (development)
- **Production**: Must be set to `false`

```bash
DJANGO_DEBUG=false
```

### Secret Key

- **Setting**: `SECRET_KEY`
- **Environment Variable**: `DJANGO_SECRET_KEY`
- **Required**: Yes (production)
- **Description**: Cryptographic signing key for Django

```bash
DJANGO_SECRET_KEY=your-secret-key-here
```

⚠️ **Never commit secret keys to version control**

### Allowed Hosts

- **Setting**: `ALLOWED_HOSTS`
- **Environment Variable**: `DJANGO_ALLOWED_HOSTS`
- **Format**: Comma-separated list
- **Default**: `*` (development only)

```bash
DJANGO_ALLOWED_HOSTS=example.com,api.example.com
```

## Database Configuration

By default, the application uses PostgreSQL. Configure via environment variables:

```bash
POSTGRES_DB=app_db
POSTGRES_USER=user
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

**Database Engine**: `django.db.backends.postgresql`

## Cache Configuration

Redis is used for caching and session storage:

```bash
REDIS_URL=redis://redis:6379/1
```

**Backend**: `django_redis.cache.RedisCache`

## Security Settings

### CORS (Cross-Origin Resource Sharing)

```bash
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

- **Setting**: `CORS_ALLOWED_ORIGINS`
- **Format**: Comma-separated URLs with schemes
- **Note**: Automatically adds `http://` or `https://` if missing

### CSRF (Cross-Site Request Forgery)

```bash
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://app.example.com
```

## Static Files

### Static URL and Root

- **STATIC_URL**: `/static/`
- **STATIC_ROOT**: `{BASE_DIR}/staticfiles`
- **STATICFILES_DIRS**: `[{BASE_DIR}/ui/static]`

### WhiteNoise Configuration

The project uses WhiteNoise for efficient static file serving:

- **Storage**: `whitenoise.storage.CompressedManifestStaticFilesStorage`
- **Middleware**: `whitenoise.middleware.WhiteNoiseMiddleware`

### Collecting Static Files

```bash
python src/manage.py collectstatic --noinput
```

## Logging Configuration

Logging is configured with multiple handlers and formatters:

### Log Files

- **General Logs**: `logs/django.json` (JSON format, rotating)
- **Proxy Logs**: `logs/proxy.json` (JSON format, rotating)
- **Error Logs**: `logs/django_error.log` (ERROR level only)
- **Debug Logs**: `logs/django_debug.log` (DEBUG level)

### Log Rotation

- **Max Size**: 10 MB per file
- **Backup Count**: 3 files
- **Formatter**: JSON (pythonjsonlogger)

### Environment Variables

```bash
LOG_JSON_PATH=logs/django.json
PROXY_LOG_JSON_PATH=logs/proxy.json
```

## API Documentation Settings

### drf-spectacular Configuration

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'aivonx proxy API',
    'DESCRIPTION': 'API documentation for aivonx proxy',
    'VERSION': '1.0.0',
}
```

### API Documentation URLs

- **OpenAPI Schema**: `/api/schema`
- **Swagger UI**: `/swagger`
- **ReDoc**: `/redoc`

## REST Framework Configuration

### Authentication

- JWT (SimpleJWT)
- Session Authentication
- Token Authentication

### Permissions

**Default**: `IsAuthenticated` (all endpoints require authentication unless explicitly set to `AllowAny`)

### Pagination

- **Class**: `LimitOffsetPagination`
- **Page Size**: 100 items
- **Parameters**: `?limit=N&offset=M`

### Schema Generation

**Class**: `drf_spectacular.openapi.AutoSchema`

## Authentication Settings

### Login/Logout URLs

- **LOGIN_URL**: `/`
- **LOGIN_REDIRECT_URL**: `/ui/manage`
- **LOGOUT_REDIRECT_URL**: `/`

### Default Root Password

```bash
ROOT_PASSWORD=changeme
```

## Template Configuration

Template directories:
- `{BASE_DIR}/ui/templates`
- `{BASE_DIR}/proxy/templates`
- `{BASE_DIR}/logviewer/templates`

## Internationalization

- **Language Code**: `zh-hant` (Traditional Chinese)
- **Time Zone**: `Asia/Taipei`
- **USE_I18N**: `True`
- **USE_TZ**: `True`

## Middleware Stack

1. `django.middleware.security.SecurityMiddleware`
2. `django.contrib.sessions.middleware.SessionMiddleware`
3. `django.middleware.common.CommonMiddleware`
4. `django.middleware.csrf.CsrfViewMiddleware`
5. `django.contrib.auth.middleware.AuthenticationMiddleware`
6. `django.contrib.messages.middleware.MessageMiddleware`
7. `django.middleware.clickjacking.XFrameOptionsMiddleware`
8. `corsheaders.middleware.CorsMiddleware`
9. `whitenoise.middleware.WhiteNoiseMiddleware`

## Installed Applications

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
