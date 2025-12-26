# API 文件

Aivonx Proxy 的完整 API 參考，所有端點使用 OpenAPI 3.0 規範記錄。

## 互動式文件

啟動應用後可存取互動式 API 文件：

- **Swagger UI**：http://localhost:8000/swagger
- **ReDoc**：http://localhost:8000/redoc
- **OpenAPI Schema**：http://localhost:8000/api/schema

## 核心端點範例

### 健康檢查

**Endpoint**：`GET /api/health`

**描述**：應用程式的全域健康檢查

**回應範例**：

```json
{
  "status": "healthy"
}
```

## Proxy 管理 API

所有 proxy 管理端點位於 `/api/proxy/`，多數需驗證。

### Proxy 狀態

**Endpoint**：`GET /api/proxy/state`

**認證**：AllowAny（不需驗證）

**描述**：檢視目前代理管理器狀態，包括 active/standby 池、節點對應、延遲與活動請求數。

回應會包含節點列表、延遲與模型清單等資訊（詳見英文原檔）。

## 節點管理 API

### 列表/建立/更新/刪除 節點

Endpoint：`GET/POST/PUT/PATCH/DELETE /api/proxy/nodes`（由 `NodeViewSet` 管理）

## Proxy 端點（Ollama 相容）

- `POST /api/generate` - 產生文本
- `POST /api/chat` - 聊天生成
- `POST /api/embed` - 單筆 embedding
- `POST /api/embeddings` - 批次 embedding
- `GET /api/tags` - 列出可用模型
- `GET /api/ps` - 列出正在執行的模型

實作位置：`src/proxy/views_proxy.py`

## 模型與序列化

詳細欄位請參考：
- `src/proxy/models.py`
- `src/proxy/serializers.py`