# API 文件

Aivonx Proxy 的完整 API 參考。所有端點使用 OpenAPI 3.0 規範記錄。

## 互動式文件

啟動應用後可存取互動式 API 文件：

- **Swagger UI**: http://localhost:8000/swagger
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/api/schema

## 核心端點

### 健康檢查

**Endpoint**: `GET /api/health`

**描述**: 全域健康檢查

**回應**:
```json
{
  "status": "healthy"
}
```

## Proxy 管理 API

所有 proxy 管理端點位於 `/api/proxy/`。多數需驗證。

### Proxy 狀態

**Endpoint**: `GET /api/proxy/state`

**認證**: Not required (AllowAny)

**描述**: 檢視目前代理管理器狀態，包括 active/standby 池、節點對應、延遲與活動請求數。

**回應**:
```json
{
  "active": ["http://node1:11434", "http://node2:11434"],
  "standby": [],
  "node_id_map": {
    "1": "http://node1:11434",
    "2": "http://node2:11434"
  },
  "latencies": {
    "http://node1:11434": 0.123,
    "http://node2:11434": 0.145
  },
  "active_counts": {
    "http://node1:11434": 2,
    "http://node2:11434": 1
  },
  "models": {
    "http://node1:11434": ["llama2", "codellama"],
    "http://node2:11434": ["llama2", "mistral"]
  }
}
```

### Active Requests

**Endpoint**: `GET /api/proxy/active-requests`

**Query Parameters**:
- `node_id` (optional): Filter by specific node ID

**認證**: Not required (AllowAny)

**描述**: 取得所有節點或特定節點的活動請求計數。

### Pull Model

**Endpoint**: `POST /api/proxy/pull`

**認證**: Not required (AllowAny)

**描述**: 將模型拉取至一個或所有節點。

### Proxy Configuration

**Endpoint**: `GET/PUT/PATCH /api/proxy/config`

**認證**: Required (IsAuthenticated)

**描述**: 取得或更新全域 proxy 設定（選擇策略）。

## 節點管理 API

### 列表/建立/更新/刪除 節點

**Endpoints**: `GET/POST/PUT/PATCH/DELETE /api/proxy/nodes`

由 `NodeViewSet` 管理。請參閱 `src/proxy/viewsets.py`

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
- **Models**: `src/proxy/models.py`
- **Serializers**: `src/proxy/serializers.py`