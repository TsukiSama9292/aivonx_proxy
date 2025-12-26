# Requirements

## System Requirements

- **Python**: >=3.12, <3.13
- **Operating System**: Linux, macOS, or Windows (Linux recommended for production)

## Core Dependencies

All project dependencies are specified in `pyproject.toml`. Key packages include:

- **Django**: >=5.2.8 - Web framework
- **Django REST Framework**: API framework with authentication
- **drf-spectacular**: OpenAPI 3 schema generation
- **uvicorn / gunicorn**: ASGI/WSGI server options
- **Redis**: >=7.1.0 - Caching and session storage
- **django-redis**: Redis cache backend
- **PostgreSQL**: Production database (psycopg2-binary)
- **httpx**: Modern async HTTP client
- **APScheduler**: Background task scheduling

## Development Tools

Recommended for development:
- `ipykernel`: Jupyter kernel support
- `jupyterlab`: Interactive development environment
- `pytest`: Testing framework
- `mkdocs` and `mkdocs-material`: Documentation generation

## Installation

Install using `uv` (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -e .[dev]
```