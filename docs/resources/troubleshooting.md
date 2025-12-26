# Troubleshooting

Common issues and solutions for Aivonx Proxy.

## Logging and Diagnostics

### Log File Locations

- **General Logs**: `logs/django.json` (JSON format)
- **Proxy Logs**: `logs/proxy.json` (JSON format)
- **Error Logs**: `logs/django_error.log` (ERROR level only)
- **Debug Logs**: `logs/django_debug.log` (DEBUG level, if enabled)

### Viewing Logs

```bash
# Tail general logs
tail -f logs/django.json | jq

# Tail proxy logs
tail -f logs/proxy.json | jq

# View error logs
tail -f logs/django_error.log

# Docker logs
docker-compose logs -f django
```

## Common Issues

### Application Won't Start

#### Check Database Connection

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Test connection
psql -h localhost -U user -d app_db

# Check environment variables
env | grep POSTGRES
```

**Solution**: Ensure PostgreSQL service is running and credentials are correct in `.env` or environment variables.

#### Check Redis Connection

```bash
# Verify Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost ping

# Check environment variable
echo $REDIS_URL
```

**Solution**: Ensure Redis service is running and `REDIS_URL` is correctly set.

#### Missing SECRET_KEY

**Error**: `ValueError: DJANGO_SECRET_KEY environment variable is required`

**Solution**: Set `DJANGO_SECRET_KEY` in your environment:

```bash
export DJANGO_SECRET_KEY="your-secret-key-here"
# Or in .env file
echo "DJANGO_SECRET_KEY=your-secret-key-here" >> .env
```

### Node Health Check Failures

#### Symptoms

- Nodes appear as inactive in `/api/proxy/state`
- Requests return "no healthy nodes available"

#### Diagnosis

```bash
# Check node health directly
curl http://node-address:11434/api/health

# Check proxy state
curl http://localhost:8000/api/proxy/state

# Check active requests
curl http://localhost:8000/api/proxy/active-requests
```

#### Solutions

1. **Network Connectivity**: Ensure the proxy can reach the node
   ```bash
   ping node-address
   telnet node-address 11434
   ```

2. **Firewall Rules**: Check that port 11434 (or configured port) is open

3. **Node is Down**: Restart the Ollama service on the node
   ```bash
   systemctl restart ollama  # On Linux
   ```

4. **Force Refresh**: The health check runs every minute, or trigger manually:
   ```python
   from proxy.utils.proxy_manager import get_global_manager
   mgr = get_global_manager()
   mgr.refresh_from_db()
   ```

### Cache Issues

#### Stale Cache Data

**Symptoms**: State endpoint shows outdated information

**Solution**: Clear Redis cache

```bash
# Using Django shell
python src/manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# Or directly with Redis
redis-cli FLUSHDB
```

#### Redis Connection Errors

**Error**: `ConnectionError: Error connecting to Redis`

**Solution**:
1. Verify Redis is running
2. Check `REDIS_URL` format: `redis://host:port/db`
3. Test connection:
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

### Streaming Issues

#### Streaming Responses Not Working

**Symptoms**: Responses are fully buffered instead of streaming

**Cause**: Using WSGI server instead of ASGI

**Solution**: Use uvicorn or gunicorn with uvicorn workers:

```bash
# Development
uvicorn aivonx.asgi:application --reload

# Production
gunicorn aivonx.asgi:application -k uvicorn.workers.UvicornWorker --workers 4
```

### Static Files Not Loading

#### Development

**Solution**: Ensure `DEBUG=True` or run `collectstatic`

```bash
python src/manage.py collectstatic --noinput
```

#### Production

**Solution**: Verify WhiteNoise middleware is enabled and static files are collected:

```bash
python src/manage.py collectstatic --noinput --clear
```

### Database Migration Issues

#### Fake a Migration

If a migration already applied manually:

```bash
python src/manage.py migrate --fake app_name migration_name
```

#### Reset Migrations (Development Only)

⚠️ **Warning**: This will delete all data

```bash
# Drop database
dropdb app_db

# Recreate
createdb app_db

# Run migrations
python src/manage.py migrate
```

### Permission Errors

#### 403 Forbidden on API Endpoints

**Cause**: Authentication required but not provided

**Solution**: Include authentication token:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/proxy/config
```

Or log in via session authentication through the web UI.

### Performance Issues

#### High Memory Usage

**Solutions**:
1. Reduce number of workers
2. Enable Redis persistence
3. Clear old log files
4. Check for memory leaks in custom code

#### Slow Responses

**Diagnosis**:
```bash
# Check node latencies
curl http://localhost:8000/api/proxy/state | jq '.latencies'

# Check active request counts
curl http://localhost:8000/api/proxy/active-requests
```

**Solutions**:
1. Add more nodes
2. Switch to `lowest_latency` strategy
3. Increase worker count
4. Check network latency to nodes

## Debug Mode

### Enable Debug Logging

In `src/aivonx/settings.py`, temporarily increase log level:

```python
LOGGING = {
    # ...
    'loggers': {
        'proxy': {
            'handlers': ['console', 'proxy_file'],
            'level': 'DEBUG',  # Changed from INFO
            'propagate': False,
        },
    },
}
```

### Django Debug Toolbar

For development, install Django Debug Toolbar:

```bash
pip install django-debug-toolbar
```

## Getting Help

1. **Check Logs**: Review log files for error messages
2. **API State**: Use `/api/proxy/state` to inspect manager state
3. **Health Checks**: Verify all services are healthy
4. **GitHub Issues**: Search or open an issue on the repository

## Useful Commands for Debugging

```bash
# System check
python src/manage.py check --deploy

# Show current settings
python src/manage.py diffsettings

# Database shell
python src/manage.py dbshell

# Python shell with Django context
python src/manage.py shell

# Show URL patterns
python src/manage.py show_urls  # Requires django-extensions

# Test Redis connection
redis-cli -h localhost ping

# Test PostgreSQL connection
psql -h localhost -U user -d app_db -c 'SELECT 1;'
```