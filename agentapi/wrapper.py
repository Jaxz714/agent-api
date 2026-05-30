"""Agent wrapping logic — execute CLI commands or Python functions."""

from __future__ import annotations

import asyncio
import importlib
import shlex
import time
from typing import Any

from agentapi.models import AgentConfig


async def run_cli_agent(config: AgentConfig, input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute a CLI command, substituting {input} with JSON-serialized input_data."""
    import json

    input_json = json.dumps(input_data)
    # Replace {input} placeholder in the command string
    command = config.command.replace("{input}", input_json)
    # Also support {input.field} style if needed in future

    start = time.monotonic()
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=config.timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "success": False,
            "error": f"Command timed out after {config.timeout}s",
            "output": "",
        }

    duration_ms = (time.monotonic() - start) * 1000
    output = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    return {
        "success": proc.returncode == 0,
        "output": output,
        "error": err if proc.returncode != 0 else "",
        "exit_code": proc.returncode,
        "duration_ms": round(duration_ms, 2),
    }


async def run_python_agent(config: AgentConfig, input_data: dict[str, Any]) -> dict[str, Any]:
    """Import a Python module and call the configured function."""
    if not config.module or not config.function:
        return {"success": False, "error": "module and function must be set for type='python'"}

    try:
        mod = importlib.import_module(config.module)
        fn = getattr(mod, config.function)
    except Exception as exc:
        return {"success": False, "error": f"Import error: {exc}"}

    start = time.monotonic()
    try:
        if asyncio.iscoroutinefunction(fn):
            result = await asyncio.wait_for(fn(input_data), timeout=config.timeout)
        else:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fn, input_data),
                timeout=config.timeout,
            )
    except asyncio.TimeoutError:
        return {"success": False, "error": f"Function timed out after {config.timeout}s"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    duration_ms = (time.monotonic() - start) * 1000
    return {
        "success": True,
        "output": result,
        "duration_ms": round(duration_ms, 2),
    }


async def execute_agent(config: AgentConfig, input_data: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the correct runner based on agent type."""
    if config.type == "cli":
        return await run_cli_agent(config, input_data)
    elif config.type == "python":
        return await run_python_agent(config, input_data)
    else:
        return {"success": False, "error": f"Unknown agent type: {config.type}"}
