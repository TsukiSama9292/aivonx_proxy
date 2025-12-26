# 程式碼結構

專案架構與組織概覽。

## 專案佈局

```
aivonx_proxy/
├── src/                      # 應用程式原始碼
│   ├── aivonx/              # Django 專案設定
│   ├── proxy/               # 核心 proxy 應用
│   ├── account/             # 認證與使用者管理
│   ├── logviewer/           # 日誌檢視介面
│   ├── ui/                  # 前端模板與靜態檔
│   ├── staticfiles/         # 收集後的靜態檔（生成）
│   ├── logs/                # 應用日誌
│   └── manage.py            # Django 管理腳本
├── docs/                    # 文件
├── docker-compose.yml       # Docker Compose 設定
├── Dockerfile               # 容器映像定義
├── pyproject.toml          # 專案 metadata 與相依
├── mkdocs.yml              # 文件設定
└── README.md               # 專案概覽
```

## 核心應用

### aivonx/（專案設定）

**用途**：Django 專案設定與核心組態

**重要檔案**：
- `settings.py` - 主要設定（資料庫、Redis、CORS/CSRF、LOG、REST framework、drf-spectacular）
- `urls.py` - 路由
- `wsgi.py` / `asgi.py` - 應用進入點
- `utils.py` - 設定相關工具函式
- `views.py` - 健康檢查與版本檢視

### proxy/（核心應用）

**用途**：主要 proxy 邏輯與節點管理

**結構概覽**：

```
proxy/
├── models.py
├── serializers.py
├── views.py
├── views_proxy.py
├── viewsets.py
├── urls.py
├── apps.py
├── admin.py
├── forms.py
├── signals.py
├── streaming.py
├── web.py
├── utils/
│   └── proxy_manager.py
├── tests/
├── templates/
├── static/
└── migrations/
```

（此處省略重複細節，請參考英文原檔）

## 重要設計模式

- **Proxy Manager Singleton**：於應用啟動時建立並透過 `get_global_manager()` 存取，使用 Redis 做跨程序通訊
- **Model-Aware Routing**：僅將請求路由到具備所需模型的節點
- **Health Check Scheduler**：預設每 60 秒檢查節點健康與模型清單

## 請求流程與資料流

簡化流程：Client → Django 路由 → API View → Proxy Manager → Node Selection → HTTPX → Ollama Node → 回傳