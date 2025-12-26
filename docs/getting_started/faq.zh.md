# 常見問題

## 一般問題

### 什麼是 Aivonx Proxy？

Aivonx Proxy 是一個反向代理與管理平台，用於多個 Ollama 模型服務節點，提供智慧路由、負載平衡與高可用性功能，並透過 REST API 與網頁管理介面操作。

### 它解決什麼問題？

它解決了管理多個 Ollama 實例的挑戰，例如：
- 提供統一的 API 端點
- 自動將請求路由到健康的節點
- 根據節點可用性與效能進行負載平衡
- 支援依模型可用性進行路由

## API 文件

### 如何檢視 API 文件？

啟動應用後可存取互動式 API 文件：
- **Swagger UI**：`/swagger`
- **ReDoc**：`/redoc`

### 有哪些 API 端點？

主要端點包括：
- `/api/proxy/nodes` - 節點 CRUD
- `/api/proxy/state` - 檢視代理狀態
- `/api/proxy/active-requests` - 監控每節點的活動請求數
- `/api/proxy/pull` - 拉取模型到節點
- `/api/generate` - 文字生成
- `/api/chat` - 聊天生成
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

**透過 Web UI：**
1. 登入管理介面
2. 前往 Nodes 頁面
3. 點選「Add Node」並填入資訊

系統會自動對新節點執行健康檢查。

### 節點選擇如何運作？

代理使用可設定的策略：
- **Least Active（預設）**：選擇活動請求最少的節點
- **Lowest Latency**：選擇延遲最低的節點

可透過 `/api/proxy/config` 變更策略。

### 節點故障處理？

健康檢查排程（預設每分鐘）會自動：
- 偵測異常節點
- 將其移到 standby 池
- 停止將新請求路由到該節點
- 節點恢復時自動重新加入

## 疑難排解

### 日誌位置

- `logs/django.json` - 一般 Django 日誌
- `logs/proxy.json` - 代理相關日誌
- `logs/django_error.log` - 錯誤日誌

### 如何檢查節點是否健康？

使用狀態端點：

```bash
curl http://localhost:8000/api/proxy/state
```

會回傳 active/standby 池、延遲與活動請求數等資訊。

### 串流回應失效

請確認使用 ASGI 伺服器（uvicorn）而非同步的 WSGI，因為串流需要非同步支援。

## 設定

### 可否變更健康檢查間隔？

是，修改 APScheduler 設定或在 proxy app 中調整排程即可。

### 如何保護 API？

API 支援：
- JWT（djangorestframework-simplejwt）
- Session 與 Token 驗證

生產環境請設定正確的 CORS 與 CSRF 受信來源。