# CLI 指令

Django 管理指令與常用操作。

## 常用指令

- `python src/manage.py migrate` — 執行資料庫遷移
- `python src/manage.py createsuperuser` — 建立管理員帳號
- `python src/manage.py test` — 執行測試
- `python src/manage.py collectstatic` — 收集靜態檔
- `python src/manage.py runserver` — 啟動開發伺服器（WSGI）

## 開發伺服器（ASGI 推薦）

使用 uvicorn（ASGI，建議用於串流）：

```bash
uv run main.py --reload --port 8000
```

## Docker 環境

在容器內執行指令：

```bash
docker-compose run --rm web python src/manage.py migrate
```

## 互動 Shell

使用 Django shell 進行互動式測試：

```bash
python src/manage.py shell
```