"""Configuration loading and management."""

from __future__ import annotations

from pathlib import Path

import yaml

from agentapi.models import ServerConfig

DEFAULT_CONFIG_PATH = Path("agent.yaml")


def load_config(path: Path | str | None = None) -> ServerConfig:
    """Load server configuration from a YAML file.

    Falls back to defaults if the file does not exist.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return ServerConfig()
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ServerConfig.from_dict(data)


def write_default_config(path: Path | str | None = None) -> Path:
    """Write a sample configuration file and return its path."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    sample = {
        "name": "My Agent API",
        "description": "Wraps my cool agent as an API",
        "port": 8000,
        "auth": {
            "enabled": True,
            "api_keys": ["sk-test-key-123"],
        },
        "rate_limit": {
            "requests_per_minute": 60,
        },
        "agents": [
            {
                "name": "chat",
                "type": "cli",
                "command": "python my_agent.py --input '{input}'",
                "method": "POST",
                "path": "/chat",
                "description": "Chat with the agent",
            },
            {
                "name": "analyze",
                "type": "cli",
                "command": "python analyzer.py '{input}'",
                "method": "POST",
                "path": "/analyze",
                "description": "Analyze input data",
            },
        ],
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(sample, f, default_flow_style=False, sort_keys=False)
    return config_path
