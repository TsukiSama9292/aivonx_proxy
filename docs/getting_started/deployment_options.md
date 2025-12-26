# Deployment Options

Aivonx Proxy supports multiple deployment strategies to fit different use cases and environments.

## 1. Docker Compose (Recommended for Development)

Use the provided `docker-compose.yml` for an all-in-one deployment:

```bash
docker-compose up -d
```

Includes:
- Django application server
- PostgreSQL database
- Redis cache
- Ollama service (optional)

## 2. Kubernetes (Production)

For production Kubernetes deployments:
- Use PostgreSQL and Redis as managed services
- Configure horizontal pod autoscaling
- Set resource limits and requests
- Use ingress for SSL/TLS termination

## 3. ASGI Server (Recommended for Streaming)

For real-time streaming endpoints and WebSocket support:

```bash
# Using uvicorn
uvicorn aivonx.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn aivonx.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
```

## 4. WSGI Server (Traditional Deployment)

For synchronous workloads:

```bash
gunicorn aivonx.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Environment Variables

Critical environment variables (see `src/aivonx/settings.py` for complete list):

### Required for Production

- `DJANGO_SECRET_KEY`: **Required** - Cryptographic secret for Django
- `DJANGO_DEBUG`: Set to `false` for production
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hostnames

### Database Configuration

- `POSTGRES_DB`: Database name (default: `app_db`)
- `POSTGRES_USER`: Database user (default: `user`)
- `POSTGRES_PASSWORD`: Database password (default: `password`)
- `POSTGRES_HOST`: Database host (default: `postgres`)
- `POSTGRES_PORT`: Database port (default: `5432`)

### Cache Configuration

- `REDIS_URL`: Redis connection URL (default: `redis://redis:6379/1`)

### Security Configuration

- `DJANGO_CORS_ALLOWED_ORIGINS`: Comma-separated allowed CORS origins
- `DJANGO_CSRF_TRUSTED_ORIGINS`: Comma-separated trusted CSRF origins
- `ROOT_PASSWORD`: Password for default `root` user

## Production Checklist

- [ ] Set strong `DJANGO_SECRET_KEY`
- [ ] Disable debug mode (`DJANGO_DEBUG=false`)
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use managed PostgreSQL and Redis
- [ ] Set up SSL/TLS certificates
- [ ] Configure logging and monitoring
- [ ] Change default `root` password
- [ ] Set up automated backups
- [ ] Configure firewall rules
