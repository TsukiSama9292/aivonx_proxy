# 常見問題

## 一般問題

### 什麼是 Aivonx Proxy？

Aivonx Proxy 是一個用於多個 Ollama 模型服務節點的反向代理和管理平台。它透過 REST API 和網頁式管理介面提供智慧路由、負載平衡和高可用性功能。

### 它解決了什麼問題？

它透過以下方式解決管理多個 Ollama 實例的挑戰：
- 提供統一的 API 端點
- 自動將請求路由到健康的節點
- 基於節點可用性和效能進行負載平衡
- 支援模型感知路由（請求僅傳送到具有所需模型的節點）

## API 文件

### 如何檢視 API 文件？

啟動應用程式後，在以下位置存取互動式 API 文件：
- **Swagger UI**：`/swagger`
- **ReDoc**：`/redoc`

這些由 drf-spectacular 自動生成，並提供互動式請求測試。

### 有哪些 API 端點可用？

關鍵端點包括：
- `/api/proxy/nodes` - 節點的 CRUD 操作
- `/api/proxy/state` - 檢視代理管理員狀態
- `/api/proxy/active-requests` - 監控每個節點的活躍請求
- `/api/proxy/pull` - 將模型拉取到節點
- `/api/generate` - 生成補全
- `/api/chat` - 聊天補全
- `/api/tags` - 列出可用模型

## 節點管理

### 如何新增節點？

**透過 API：**
```bash
curl -X POST http://localhost:8000/api/proxy/nodes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "node1",
    "address": "192.168.1.100",
    "port": 11434
  }'
```

**透過網頁 UI：**
1. 登入管理介面
2. 導航到節點區段
3. 點擊「新增節點」並填入詳細資訊

系統會自動對新節點執行健康檢查。

### 節點選擇如何運作？

代理使用可配置的策略：
- **最少活躍**（預設）：路由到活躍請求最少的節點
- **最低延遲**：路由到回應時間最好的節點

您可以透過 `/api/proxy/config` 端點變更策略。

### 如果節點當機會發生什麼？

健康檢查排程器（預設每分鐘執行一次）會自動：
- 偵測不健康的節點
- 將它們移至待命池
- 停止將新請求路由到它們
- 當它們恢復時重新新增

## 故障排除

### 日誌在哪裡？

日誌儲存在：
- `logs/django.json` - 一般 Django 日誌
- `logs/proxy.json` - 代理特定日誌
- `logs/django_error.log` - 錯誤日誌

### 如何檢查節點是否健康？

使用狀態端點：
```bash
curl http://localhost:8000/api/proxy/state
```

這會返回活躍和待命池、延遲以及活躍請求計數。

### 串流回應無法運作

確保您使用 ASGI 伺服器（uvicorn）而非 WSGI（gunicorn 與同步工作者）。串流需要非同步支援。

## 配置

### 我可以變更健康檢查間隔嗎？

是的，修改 Django 設定中的 APScheduler 配置，或直接在代理應用配置中調整排程器。

### 如何保護 API？

API 使用：
- JWT 認證（透過 djangorestframework-simplejwt）
- 會話認證
- Token 認證

確保在生產中設定適當的 CORS 和 CSRF 受信任來源。
