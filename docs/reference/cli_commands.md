# CLI Commands

Django management commands and common operations.

## Common Commands

- `python src/manage.py migrate` — Run database migrations
- `python src/manage.py createsuperuser` — Create admin account
- `python src/manage.py test` — Run tests
- `python src/manage.py collectstatic` — Collect static files
- `python src/manage.py runserver` — Start development server (WSGI)

## Development Server

Using uvicorn (ASGI, recommended for streaming):

```bash
uv run main.py --reload --port 8000
```

## Docker Environment

Run commands in container:

```bash
docker-compose run --rm web python src/manage.py migrate
```

## Interactive Shell

Use Django shell for interactive testing:

```bash
python src/manage.py shell
```
