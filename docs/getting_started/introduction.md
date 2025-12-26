# Introduction

Aivonx Proxy is a Django-based reverse proxy and management service designed for Ollama model-serving nodes.

## Key Features

- **Node Management**: Manage multiple model service nodes with active/standby pool distribution
- **REST API**: Comprehensive endpoints for node management, model pulling, state monitoring, and health checks
- **Web UI**: Built-in administrative interface (located in `ui/` and `proxy.web`) for login and management

## Core Components

- **Source Root**: `src/`
- **Project Settings**: `src/aivonx/settings.py`
- **Proxy Logic**: `src/proxy/`

## Architecture Overview

The proxy acts as a unified gateway that intelligently routes requests to backend Ollama nodes based on:
- Model availability
- Node health status
- Load balancing strategy (least active or lowest latency)
- Real-time monitoring and failover
