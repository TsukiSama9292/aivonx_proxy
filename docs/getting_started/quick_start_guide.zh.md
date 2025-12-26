# 快速上手指南

## 選項 1：Docker Compose（建議）

最快上手的方式是從專案根目錄使用 Docker Compose：

```bash
# 標準部署
docker-compose up --build

# 或使用測試組態
docker-compose -f docker-compose-test.yml up --build
```

啟動後存取介面：
- **Web UI**：http://localhost:8000
- **API 文件**：http://localhost:8000/swagger 或 http://localhost:8000/redoc

### 預設帳號

- **使用者名稱**：`root`
- **密碼**：`changeme`

⚠️ **重要**：請透過 `.env` 設定 `ROOT_PASSWORD` 來修改預設密碼。

## 選項 2：本機開發伺服器

本機開發（支援熱重載）：

```bash
# 安裝相依
uv sync

# 執行 migrations
python src/manage.py migrate

# 啟動 ASGI 開發（含 reload）
uv run main.py --reload --port 8000

# 或使用 Django 開發伺服器（WSGI）
python src/manage.py runserver
```

## 檢視文件

本機啟動文件伺服：

```bash
mkdocs serve -f mkdocs.yml
```

網址通常為：http://localhost:8000（或 mkdocs 指定的 port）

## 靜態檔案

在本機 ASGI 運行時，修改靜態檔後請執行：

```bash
python src/manage.py collectstatic --noinput
```