"""Data models for Agent API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for a single agent endpoint."""

    name: str
    type: str  # "cli" or "python"
    command: str = ""
    module: str = ""
    function: str = ""
    method: str = "POST"
    path: str = ""
    timeout: int = 30
    description: str = ""


@dataclass
class AuthConfig:
    """Authentication configuration."""

    enabled: bool = True
    api_keys: list[str] = field(default_factory=list)
    header_name: str = "X-API-Key"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    requests_per_minute: int = 60


@dataclass
class ServerConfig:
    """Full server configuration."""

    name: str = "Agent API"
    description: str = "API service powered by Agent API"
    port: int = 8000
    host: str = "0.0.0.0"
    auth: AuthConfig = field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    agents: list[AgentConfig] = field(default_factory=list)
    database: str = "agentapi.db"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerConfig:
        """Create config from a dictionary (e.g. parsed YAML)."""
        auth_data = data.get("auth", {})
        auth = AuthConfig(
            enabled=auth_data.get("enabled", True),
            api_keys=auth_data.get("api_keys", []),
            header_name=auth_data.get("header_name", "X-API-Key"),
        )
        rl_data = data.get("rate_limit", {})
        rate_limit = RateLimitConfig(
            requests_per_minute=rl_data.get("requests_per_minute", 60),
        )
        agents = []
        for a in data.get("agents", []):
            agents.append(AgentConfig(
                name=a.get("name", ""),
                type=a.get("type", "cli"),
                command=a.get("command", ""),
                module=a.get("module", ""),
                function=a.get("function", ""),
                method=a.get("method", "POST"),
                path=a.get("path", f"/{a.get('name', '')}"),
                timeout=a.get("timeout", 30),
                description=a.get("description", ""),
            ))
        return cls(
            name=data.get("name", "Agent API"),
            description=data.get("description", ""),
            port=data.get("port", 8000),
            host=data.get("host", "0.0.0.0"),
            auth=auth,
            rate_limit=rate_limit,
            agents=agents,
            database=data.get("database", "agentapi.db"),
        )


@dataclass
class RequestLog:
    """A logged request."""

    id: int = 0
    timestamp: str = ""
    method: str = ""
    path: str = ""
    status_code: int = 0
    client_ip: str = ""
    request_body: str = ""
    response_body: str = ""
    duration_ms: float = 0.0
    api_key_prefix: str = ""
