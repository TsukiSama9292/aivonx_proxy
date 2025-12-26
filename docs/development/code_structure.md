# Code Structure

Overview of the project's architecture and organization.

## Project Layout

```
aivonx_proxy/
├── src/                      # Application source code
│   ├── aivonx/              # Django project configuration
│   ├── proxy/               # Core proxy application
│   ├── account/             # Authentication and user management
│   ├── logviewer/           # Log viewing interface
│   ├── ui/                  # Frontend templates and static files
│   ├── staticfiles/         # Collected static files (generated)
│   ├── logs/                # Application logs
│   └── manage.py            # Django management script
├── docs/                    # Documentation
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Container image definition
├── pyproject.toml          # Project metadata and dependencies
├── mkdocs.yml             # Documentation configuration
└── README.md              # Project overview
```

## Core Applications

### aivonx/ (Project Configuration)

**Purpose**: Django project settings and core configuration

**Key Files**:
- `settings.py` - Main configuration file
  - Database settings (PostgreSQL)
  - Redis cache configuration
  - Security settings (CORS, CSRF, SECRET_KEY)
  - Logging configuration
  - REST Framework settings
  - drf-spectacular settings
- `urls.py` - URL routing
- `wsgi.py` - WSGI application entry point
- `asgi.py` - ASGI application entry point
- `utils.py` - Utility functions for settings
- `views.py` - Health check and version views

### proxy/ (Core Application)

**Purpose**: Main proxy logic and node management

**Structure**:
```
proxy/
├── models.py              # Database models (Node, ProxyConfig)
├── serializers.py         # DRF serializers
├── views.py              # API views (state, health, config)
├── views_proxy.py        # Proxy endpoints (generate, chat, embed)
├── viewsets.py           # REST viewsets (NodeViewSet)
├── urls.py               # URL routing
├── apps.py               # App configuration (lifecycle hooks)
├── admin.py              # Django admin configuration
├── forms.py              # Web forms
├── signals.py            # Django signals
├── streaming.py          # Streaming response utilities
├── web.py                # Web UI views
├── utils/                # Utility modules
│   └── proxy_manager.py  # HA manager and node selection
├── tests/                # Test suite
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS)
└── migrations/           # Database migrations
```

**Key Components**:

1. **Models** (`models.py`)
   - `Node`: Backend Ollama server definition
   - `ProxyConfig`: Global proxy configuration

2. **Proxy Manager** (`utils/proxy_manager.py`)
   - Node selection algorithms
   - Health monitoring
   - Active/standby pool management
   - Latency tracking
   - Model discovery

3. **API Views** (`views.py`, `viewsets.py`)
   - Node CRUD operations
   - State inspection
   - Configuration management
   - Model pulling

4. **Proxy Endpoints** (`views_proxy.py`)
   - `/api/generate` - Text generation
   - `/api/chat` - Chat completions
   - `/api/embed` - Single embedding
   - `/api/embeddings` - Batch embeddings
   - `/api/tags` - List models
   - `/api/ps` - Running models

### account/ (User Management)

**Purpose**: User authentication and account management

**Key Files**:
- `models.py` - User models (if any custom models)
- `serializers.py` - User serializers
- `views.py` - Authentication views
- `urls.py` - Account URL routing

### logviewer/ (Log Viewer)

**Purpose**: Web interface for viewing JSON logs

**Key Files**:
- `views.py` - Log retrieval API
- `web.py` - Log viewer UI
- `templates/` - Log viewer HTML
- `static/` - Log viewer CSS/JS

### ui/ (Frontend)

**Purpose**: Static files and templates for web interface

**Structure**:
```
ui/
├── static/
│   ├── css/
│   └── js/
└── templates/
```

## Key Architectural Patterns

### Proxy Manager Singleton

The proxy manager is initialized as a singleton:
- Created during app startup (ASGI lifespan events)
- Accessible via `get_global_manager()`
- Manages shared state across workers
- Uses Redis for cross-process communication

### Model-Aware Routing

1. Client requests model by name
2. Manager checks which nodes have the model
3. Selects best available node using strategy
4. Routes request to selected node
5. Tracks active requests
6. Releases node when complete

### Health Check Scheduler

- Runs every 60 seconds (configurable)
- Checks all configured nodes
- Updates active/standby pools
- Refreshes model availability
- Measures latency

## Data Flow

### Request Flow

```
Client Request
    ↓
Django URL Router
    ↓
API View (views_proxy.py)
    ↓
Proxy Manager
    ↓
Node Selection (strategy)
    ↓
HTTPX Client Request
    ↓
Ollama Node
    ↓
Streaming Response
    ↓
Client
```

### Node State Management

```
Database (PostgreSQL)
    ↓
Proxy Manager
    ↓
Redis Cache
    ↓
Active/Standby Pools
    ↓
Request Selection
```

## Important Files Reference

### Configuration
- `src/aivonx/settings.py` - All settings
- `pyproject.toml` - Dependencies
- `docker-compose.yml` - Services

### Core Logic
- `src/proxy/utils/proxy_manager.py` - HA manager
- `src/proxy/views_proxy.py` - Proxy endpoints
- `src/proxy/models.py` - Data models

### API
- `src/aivonx/urls.py` - Main routing
- `src/proxy/urls.py` - Proxy routing
- `src/proxy/viewsets.py` - REST viewsets

## Design Principles

1. **Separation of Concerns**: Each app handles specific functionality
2. **DRY (Don't Repeat Yourself)**: Shared utilities in utils/
3. **Scalability**: Stateless design with Redis for shared state
4. **Testability**: Clear interfaces and dependency injection
5. **Maintainability**: Clear naming and documentation