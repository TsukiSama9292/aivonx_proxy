# Quick Start Guide

## Option 1: Docker Compose (Recommended)

The fastest way to get started is using Docker Compose from the project root:

```bash
# Standard deployment
docker-compose up --build

# Or use the test configuration
docker-compose -f docker-compose-test.yml up --build
```

Once running, access the web interface at:
- **Web UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/swagger or http://localhost:8000/redoc

### Default Credentials

- **Username**: `root`
- **Password**: `changeme`

⚠️ **Important**: Change the default password by setting `ROOT_PASSWORD` in your `.env` file.

## Option 2: Local Development Server

For local development with hot-reload:

```bash
# Install dependencies
uv sync

# Run migrations
python src/manage.py migrate

# Start development server (ASGI with reload)
uv run main.py --reload --port 8000

# Alternative: Django development server (WSGI)
python src/manage.py runserver
```

## Viewing Documentation

Serve the documentation locally:

```bash
mkdocs serve -f mkdocs.yml
```

Access at: http://localhost:8000 (or the port specified by mkdocs)

## Static Files

If running locally with ASGI, collect static files after making changes:

```bash
python src/manage.py collectstatic --noinput
```