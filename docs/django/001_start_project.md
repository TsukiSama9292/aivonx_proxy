# 啟動專案

## 1. 撰寫 pytorch.toml

```
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "aivonx"
version = "0.0.0.dev0"
requires-python = ">=3.12, <3.13"
description = "aivonx"

authors = [
    { name = "Xuan‑You Lin", email = "a0985821880@gmail.com" }
]

dependencies = [
    "python-dotenv>=1.2.1",
    "pydantic>=2.12.4",

    "gunicorn>=23.0.0",
    "uvicorn>=0.38.0",
    "requests>=2.32.5",

    "django>=5.2.8",
    "django-asgi-lifespan>=0.5.0",
    "django-cors-headers>=4.9.0",
    "djangorestframework>=3.16.1",
    "djangorestframework-simplejwt>=5.5.1",
]

[dependency-groups]
dev = [
    "ipykernel",
    "ipywidgets",
    "nest_asyncio",
    "jupyterlab_widgets",
]

[tool.hatch.build.targets.wheel]
packages = ["src/"]
```

## 2. 同步套件和初始化 Django 專案

```bash
uv sync
mkdir -p src
uv run django-admin startproject aivonx src
```

## 3. 進入專案目錄

```bash
cd src
```

## 4. 建立資料庫遷移檔案

```bash
uv run src/manage.py makemigrations
```

## 5. 執行資料庫遷移檔案

```bash
uv run src/manage.py migrate
```

## 6. 運行 Django 專案

```bash
uv run manage.py runserver
```