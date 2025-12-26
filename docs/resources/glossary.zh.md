# 術語表（繁體中文）

本文件列出 Aivonx Proxy 常用的術語與概念說明。

## 核心概念

### 節點（Node）

提供模型推論能力的後端 Ollama 服務。每個節點包含：
- 唯一識別碼（ID）
- 網路位址（host:port）
- 可承載多個模型
- 活躍 / 不活躍 狀態
- 會被監控健康狀態與延遲

**資料模型**：定義於 `src/proxy/models.py`

### 活躍池（Active Pool）

目前健康且可接收請求的節點集合。活躍池中的節點：
- 通過近期健康檢查
- 可由 proxy 管理器選取
- 其延遲與當前處理中請求數會被追蹤

### 待命池（Standby Pool）

已設定但目前不健康或非活躍的節點集合。節點會在以下情況移入待命池：
- 健康檢查失敗
- 被手動設定為不活躍
- 發生連線錯誤

節點恢復後會自動移回活躍池。

### 代理管理器（Proxy Manager）

核心元件，負責：
- 維護活躍與待命池
- 為請求選取適當節點
- 追蹤延遲與活躍請求數
- 週期性執行健康檢查
- 管理節點生命週期

**實作位置**：`src/proxy/utils/proxy_manager.py`

### ProxyConfig

代理節點選擇策略的全域設定，包含：
- **策略（Strategy）**：選取演算法（`least_active` 或 `lowest_latency`）
- **最後更新時間（Updated At）**：最後修改時間戳

**資料模型**：定義於 `src/proxy/models.py`

## 選取策略

### 最少活躍（Least Active，預設）

選擇當前處理中請求數最少的節點，適用於：
- 負載平衡
- 避免單一節點過載
- 均勻分配工作

### 最低延遲（Lowest Latency）

選擇回應時間最短的節點，適用於：
- 最小化回應延遲
- 地理位置優化
- 對延遲敏感的應用

## 請求相關概念

### 活躍請求（Active Request）

節點正在處理中的請求。計數會：
- 在派送請求時遞增
- 在回應完成時遞減
- 存放於 Redis 以支援跨程序可見性
- 被 `least_active` 策略使用

### 模型感知路由（Model-Aware Routing）

代理僅會將請求路由至具有該模型的節點，確保：
- 不會因為模型不存在而發生失敗
- 有效利用節點資源
- 若模型可用性改變，會自動故障轉移

### 串流回應（Streaming Response）

逐步輸出回應（邊產生邊傳送），而非等到完整結果才回傳。優點：
- 降低首個 token 的延遲
- 改善聊天應用的使用體驗
- 減少記憶體使用量

**需求**：ASGI 伺服器（例如 `uvicorn`）

## 健康檢查與監控

### 健康檢查（Health Check）

定期向節點的 `/api/health` 發出請求以確認：
- 節點可達
- 服務有回應
- 節點應處於活躍池

**頻率**：預設每 1 分鐘

### 延遲（Latency）

健康檢查的來回時間（round-trip time），用於：
- `lowest_latency` 選取策略
- 監控與診斷
- 效能優化

**儲存**：Redis 快取

### 可用模型（Available Models）

節點上目前可用的模型清單，來源於：
- 查詢 `/api/tags` 端點
- 週期性刷新（預設每 1 分鐘）
- 手動拉取模型資訊

**儲存**：資料庫與 Redis 快取

## API 相關概念

### ViewSet

Django REST Framework 的類別，用於提供資源的 CRUD 操作。例如：
- `NodeViewSet`：節點資源管理
- 提供：列表、建立、取得、更新、刪除

**位置**：`src/proxy/viewsets.py`

### Serializer

負責在 Python 物件與 JSON 之間互相轉換，用於 API 回應。功能包含：
- 資料驗證
- 欄位層級的權限處理
- 支援巢狀關聯

**位置**：`src/proxy/serializers.py`

### JWT（JSON Web Token）

一種無狀態的認證 token，用於 API 存取，通常包含：
- 使用者識別資訊
- 到期時間
- 加密簽章

## 基礎建設

### ASGI（Asynchronous Server Gateway Interface）

現代 Python Web 伺服器介面，支援：
- 非同步（async/await）
- WebSocket
- 串流回應
- 長連線

**實作範例**：`uvicorn`, `Daphne`

### WSGI（Web Server Gateway Interface）

傳統的同步 Web 伺服器介面，用於：
- 同步請求/回應流程
- 傳統 Web 應用

**實作範例**：`Gunicorn`, `uWSGI`

### Redis

記憶體型資料庫，用於：
- 快取節點狀態
- 儲存活躍請求計數
- Session 存放
- 任務佇列（可選）

### PostgreSQL

關聯式資料庫，用於儲存：
- 節點設定
- 代理設定
- 使用者帳號
- 稽核日誌

## Django 概念

### Migration

描述資料庫結構變更的 Python 檔案，用於：
- 對資料庫結構進行版本控制
- 部署結構變更
- 需要時回滾變更

**位置**：`src/*/migrations/`

### App Config

Django 應用設定，可用來：
- 初始化全域狀態
- 註冊 signal 處理器
- 設定應用相關參數

**範例**：`src/proxy/apps.py` 中的 proxy 管理器初始化

### Middleware

處理全域請求/回應流程的元件，包含：
- 安全標頭
- CORS
- 認證
- 日誌

## 縮寫清單

- **API**：Application Programming Interface（應用程式介面）
- **ASGI**：Asynchronous Server Gateway Interface
- **CORS**：Cross-Origin Resource Sharing（跨來源資源共用）
- **CRUD**：Create, Read, Update, Delete（新增、讀取、更新、刪除）
- **CSRF**：Cross-Site Request Forgery（跨站請求偽造）
- **DRF**：Django REST Framework
- **HA**：High Availability（高可用性）
- **HTTP**：Hypertext Transfer Protocol
- **HTTPS**：HTTP Secure（安全的 HTTP）
- **JSON**：JavaScript Object Notation
- **JWT**：JSON Web Token
- **REST**：Representational State Transfer
- **SSL**：Secure Sockets Layer
- **TLS**：Transport Layer Security
- **UI**：User Interface（使用者介面）
- **URL**：Uniform Resource Locator（統一資源定位符）
- **WSGI**：Web Server Gateway Interface