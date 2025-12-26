# Glossary

Key terms and concepts used in Aivonx Proxy.

## Core Concepts

### Node

A backend Ollama service that provides model inference capabilities. Each node:
- Has a unique identifier (ID)
- Has a network address (host:port)
- Can host multiple models
- Has an active/inactive status
- Is monitored for health and latency

**Database Model**: Defined in `src/proxy/models.py`

### Active Pool

A collection of nodes that are currently healthy and available to receive requests. Nodes in the active pool:
- Passed recent health checks
- Can be selected by the proxy manager
- Have their latency and active request counts tracked

### Standby Pool

A collection of nodes that are configured but currently unhealthy or inactive. Nodes move to standby when:
- Health checks fail
- They are manually set to inactive
- Connection errors occur

Nodes are automatically moved back to active pool when they recover.

### Proxy Manager

The core component responsible for:
- Maintaining active and standby node pools
- Selecting appropriate nodes for requests
- Tracking latency and active request counts
- Performing periodic health checks
- Managing node lifecycle

**Implementation**: Located in `src/proxy/utils/proxy_manager.py`

### ProxyConfig

Global configuration for the proxy's node selection strategy. Contains:
- **Strategy**: Selection algorithm (`least_active` or `lowest_latency`)
- **Updated At**: Last modification timestamp

**Database Model**: Defined in `src/proxy/models.py`

## Selection Strategies

### Least Active (Default)

Selects the node with the fewest currently active requests. Best for:
- Load balancing
- Preventing overload on single nodes
- Distributing work evenly

### Lowest Latency

Selects the node with the best (lowest) response time. Best for:
- Minimizing response time
- Geographic optimization
- Performance-critical applications

## Request Concepts

### Active Request

A request currently being processed by a node. The count is:
- Incremented when a request is dispatched
- Decremented when the response completes
- Stored in Redis for cross-process visibility
- Used by the `least_active` selection strategy

### Model-Aware Routing

The proxy only routes requests to nodes that have the requested model available. This ensures:
- Requests never fail due to missing models
- Efficient use of node resources
- Automatic failover if model availability changes

### Streaming Response

A response sent incrementally as it's generated, rather than waiting for completion. Benefits:
- Lower latency to first token
- Better user experience for chat applications
- Reduced memory usage

**Requirement**: ASGI server (uvicorn)

## Health and Monitoring

### Health Check

A periodic request to a node's `/api/health` endpoint to verify:
- Node is reachable
- Service is responding
- Node should be in active pool

**Frequency**: Every 1 minute (default)

### Latency

The round-trip time for a health check request to a node. Used by:
- `lowest_latency` selection strategy
- Monitoring and diagnostics
- Performance optimization

**Storage**: Redis cache

### Available Models

List of models currently available on a node, discovered through:
- `/api/tags` endpoint queries
- Periodic refresh (every 1 minute)
- Manual model pulls

**Storage**: Both database and Redis cache

## API Concepts

### ViewSet

A Django REST Framework class that provides CRUD operations for a resource. Example:
- `NodeViewSet`: Manages node resources
- Provides: list, create, retrieve, update, delete

**Location**: `src/proxy/viewsets.py`

### Serializer

A component that converts between Python objects and JSON for API responses. Provides:
- Data validation
- Field-level permissions
- Nested relationships

**Location**: `src/proxy/serializers.py`

### JWT (JSON Web Token)

A stateless authentication token used for API access. Contains:
- User identity
- Expiration time
- Cryptographic signature

## Infrastructure

### ASGI (Asynchronous Server Gateway Interface)

Modern Python web server interface supporting:
- Async/await
- WebSockets
- Streaming responses
- Long-lived connections

**Implementation**: uvicorn, Daphne

### WSGI (Web Server Gateway Interface)

Traditional Python web server interface for:
- Synchronous request/response
- Traditional web applications

**Implementation**: Gunicorn, uWSGI

### Redis

In-memory data store used for:
- Caching node state
- Storing active request counts
- Session storage
- Task queue (optional)

### PostgreSQL

Relational database used for:
- Node configuration
- Proxy configuration
- User accounts
- Audit logs

## Django Concepts

### Migration

A Python file that describes changes to database schema. Used to:
- Version control database structure
- Deploy schema changes
- Roll back changes if needed

**Location**: `src/*/migrations/`

### App Config

Django application configuration that can:
- Initialize global state
- Register signal handlers
- Configure application-specific settings

**Example**: Proxy manager initialization in `src/proxy/apps.py`

### Middleware

Components that process requests/responses globally:
- Security headers
- CORS
- Authentication
- Logging

## Acronyms

- **API**: Application Programming Interface
- **ASGI**: Asynchronous Server Gateway Interface
- **CORS**: Cross-Origin Resource Sharing
- **CRUD**: Create, Read, Update, Delete
- **CSRF**: Cross-Site Request Forgery
- **DRF**: Django REST Framework
- **HA**: High Availability
- **HTTP**: Hypertext Transfer Protocol
- **HTTPS**: HTTP Secure
- **JSON**: JavaScript Object Notation
- **JWT**: JSON Web Token
- **REST**: Representational State Transfer
- **SSL**: Secure Sockets Layer
- **TLS**: Transport Layer Security
- **UI**: User Interface
- **URL**: Uniform Resource Locator
- **WSGI**: Web Server Gateway Interface
