# API Documentation

Comprehensive API reference for Aivonx Proxy. All endpoints are documented using OpenAPI 3.0 specification.

## Interactive Documentation

After starting the application, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/swagger
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/api/schema

## Core Endpoints

### Health Check

**Endpoint**: `GET /api/health`

**Description**: Global health check for the application.

**Response**:
```json
{
  "status": "healthy"
}
```

## Proxy Management API

All proxy management endpoints are under `/api/proxy/`. Most require authentication.

### Proxy State

**Endpoint**: `GET /api/proxy/state`

**Authentication**: Not required (AllowAny)

**Description**: View the current proxy manager state including active/standby pools, node mappings, latencies, and active request counts.

**Response**:
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

**Authentication**: Not required (AllowAny)

**Description**: Get active request counts for all nodes or a specific node.

### Pull Model

**Endpoint**: `POST /api/proxy/pull`

**Authentication**: Not required (AllowAny)

**Description**: Pull a model to one or all nodes.

### Proxy Configuration

**Endpoint**: `GET/PUT/PATCH /api/proxy/config`

**Authentication**: Required (IsAuthenticated)

**Description**: Get or update the global proxy configuration (selection strategy).

## Node Management API

### List/Create/Update/Delete Nodes

**Endpoints**: `GET/POST/PUT/PATCH/DELETE /api/proxy/nodes`

Managed by `NodeViewSet`. See `src/proxy/viewsets.py`

## Proxy Endpoints (Ollama Compatible)

- `POST /api/generate` - Generate completions
- `POST /api/chat` - Chat completions
- `POST /api/embed` - Single embedding
- `POST /api/embeddings` - Batch embeddings
- `GET /api/tags` - List available models
- `GET /api/ps` - List running models

Implementation: `src/proxy/views_proxy.py`

## Models and Serializers

For detailed field definitions, see:
- **Models**: `src/proxy/models.py`
- **Serializers**: `src/proxy/serializers.py`
