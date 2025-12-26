# 程式碼結構

專案架構和組織的概述。

## 專案佈局

```
aivonx_proxy/
├── src/                      # 應用程式原始碼
│   ├── aivonx/              # Django 專案配置
│   ├── proxy/               # 核心代理應用程式
│   ├── account/             # 認證和使用者管理
│   ├── logviewer/           # 日誌檢視介面
│   ├── ui/                  # 前端模板和靜態檔案
│   ├── staticfiles/         # 收集的靜態檔案（生成）
│   ├── logs/                # 應用程式日誌
│   └── manage.py            # Django 管理腳本
├── docs/                    # 文件
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile              # 容器映像定義
├── pyproject.toml          # 專案元資料和依賴
├── mkdocs.yml             # 文件配置
└── README.md              # 專案概述
```

## 核心應用程式

### aivonx/ (專案配置)

**目的**：Django 專案設定和核心配置

**關鍵檔案**：
- `settings.py` - 主要配置檔案
  - 資料庫設定（PostgreSQL）
  - Redis 快取配置
  - 安全性設定（CORS、CSRF、SECRET_KEY）
  - 日誌配置
  - REST Framework 設定
  - drf-spectacular 設定
- `urls.py` - URL 路由
- `wsgi.py` - WSGI 應用程式入口點
- `asgi.py` - ASGI 應用程式入口點
- `utils.py` - 設定工具函數
- `views.py` - 健康檢查和版本檢視

### proxy/ (核心應用程式)

**目的**：主要代理邏輯和節點管理

**結構**：
```
proxy/
├── models.py              # 資料庫模型（Node、ProxyConfig）
├── serializers.py         # DRF 序列化器
├── views.py              # API 檢視（state、health、config）
├── views_proxy.py        # 代理端點（generate、chat、embed）
├── viewsets.py           # REST viewsets（NodeViewSet）
├── urls.py               # URL 路由
├── apps.py               # 應用程式配置（生命週期鉤子）
├── admin.py              # Django 管理員配置
├── forms.py              # 網頁表單
├── signals.py            # Django 訊號
├── streaming.py          # 串流回應工具
├── web.py                # 網頁 UI 檢視
├── utils/                # 工具模組
│   └── proxy_manager.py  # HA 管理員和節點選擇
├── tests/                # 測試套件
├── templates/            # HTML 模板
├── static/               # 靜態檔案（CSS、JS）
└── migrations/           # 資料庫遷移
```

**關鍵元件**：

1. **模型** (`models.py`)
   - `Node`：後端 Ollama 伺服器定義
   - `ProxyConfig`：全域代理配置

2. **代理管理員** (`utils/proxy_manager.py`)
   - 節點選擇演算法
   - 健康監控
   - 主動/待命池管理
   - 延遲追蹤
   - 模型發現

3. **API 檢視** (`views.py`、`viewsets.py`)
   - 節點 CRUD 操作
   - 狀態檢查
   - 配置管理
   - 模型拉取

4. **代理端點** (`views_proxy.py`)
   - `/api/generate` - 文字生成
   - `/api/chat` - 聊天完成
   - `/api/embed` - 單一嵌入
   - `/api/embeddings` - 批次嵌入
   - `/api/tags` - 列出模型
   - `/api/ps` - 執行中的模型

### account/ (使用者管理)

**目的**：使用者認證和帳戶管理

**關鍵檔案**：
- `models.py` - 使用者模型（如果有任何自訂模型）
- `serializers.py` - 使用者序列化器
- `views.py` - 認證檢視
- `urls.py` - 帳戶 URL 路由

### logviewer/ (日誌檢視器)

**目的**：檢視 JSON 日誌的網頁介面

**關鍵檔案**：
- `views.py` - 日誌擷取 API
- `web.py` - 日誌檢視器 UI
- `templates/` - 日誌檢視器 HTML
- `static/` - 日誌檢視器 CSS/JS

### ui/ (前端)

**目的**：網頁介面的靜態檔案和模板

**結構**：
```
ui/
├── static/
│   ├── css/
│   └── js/
└── templates/
```

## 關鍵架構模式

### 代理管理員單例

代理管理員初始化為單例：
- 在應用程式啟動期間建立（ASGI 生命週期事件）
- 可透過 `get_global_manager()` 存取
- 管理跨工作者的共享狀態
- 使用 Redis 進行跨程序通訊

### 模型感知路由

1. 客戶端依名稱請求模型
2. 管理員檢查哪些節點有該模型
3. 使用策略選擇最佳可用節點
4. 將請求路由到選定的節點
5. 追蹤活躍請求
6. 完成時釋放節點

### 健康檢查排程器

- 每 60 秒執行一次（可配置）
- 檢查所有配置的節點
- 更新主動/待命池
- 重新整理模型可用性
- 測量延遲

## 資料流程

### 請求流程

```
客戶端請求
    ↓
Django URL 路由器
    ↓
API 檢視 (views_proxy.py)
    ↓
代理管理員
    ↓
節點選擇 (策略)
    ↓
HTTPX 客戶端請求
    ↓
Ollama 節點
    ↓
串流回應
    ↓
客戶端
```

### 節點狀態管理

```
資料庫 (PostgreSQL)
    ↓
代理管理員
    ↓
Redis 快取
    ↓
主動/待命池
    ↓
請求選擇
```

## 重要檔案參考

### 配置
- `src/aivonx/settings.py` - 所有設定
- `pyproject.toml` - 依賴
- `docker-compose.yml` - 服務

### 核心邏輯
- `src/proxy/utils/proxy_manager.py` - HA 管理員
- `src/proxy/views_proxy.py` - 代理端點
- `src/proxy/models.py` - 資料模型

### API
- `src/aivonx/urls.py` - 主要路由
- `src/proxy/urls.py` - 代理路由
- `src/proxy/viewsets.py` - REST viewsets

## 設計原則

1. **關注點分離**：每個應用程式處理特定功能
2. **DRY（不要重複自己）**：共享工具在 utils/
3. **可擴展性**：無狀態設計，使用 Redis 共享狀態
4. **可測試性**：清晰介面和依賴注入
5. **可維護性**：清晰命名和文件