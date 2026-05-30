# Agent API

Turn any AI agent into an API service — one config file, instant API with auth, rate limiting, logging, and docs.

## Features

- **CLI wrapping** — expose any command-line tool as an HTTP endpoint
- **Python function wrapping** — call Python functions directly via API
- **API key authentication** — secure your endpoints with bearer-style keys
- **Rate limiting** — per-IP sliding-window rate limiter
- **Request logging** — every request/response logged to SQLite
- **Auto-generated OpenAPI docs** at `/docs`
- **Web UI** at `/` for interactive testing
- **Health check** at `/health`

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Generate a sample config
agentapi init

# Edit agent.yaml to add your agents, then:
agentapi serve

# Open http://localhost:8000 for the web UI
# Open http://localhost:8000/docs for Swagger docs
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `agentapi init` | Create a sample `agent.yaml` |
| `agentapi serve` | Start the API server |
| `agentapi serve --port 9000` | Custom port |
| `agentapi serve --config my.yaml` | Custom config path |
| `agentapi logs` | View recent request logs |
| `agentapi keys generate` | Generate a new API key |
| `agentapi test /chat "hello"` | Test an endpoint |

## Config File (`agent.yaml`)

```yaml
name: "My Agent API"
description: "Wraps my cool agent as an API"
port: 8000

auth:
  enabled: true
  api_keys:
    - "sk-test-key-123"

rate_limit:
  requests_per_minute: 60

agents:
  - name: "chat"
    type: "cli"
    command: "python my_agent.py --input '{input}'"
    method: "POST"
    path: "/chat"
    description: "Chat with the agent"
```

## Agent Types

### CLI (`type: "cli"`)

Runs a shell command. The `{input}` placeholder is replaced with the JSON-serialized request body.

### Python (`type: "python"`)

Imports a module and calls a function. The function receives the request body as a dict.

```yaml
agents:
  - name: "analyze"
    type: "python"
    module: "my_module"
    function: "analyze"
    method: "POST"
    path: "/analyze"
```

## License

MIT
