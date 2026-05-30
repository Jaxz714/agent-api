"""FastAPI application that exposes configured agents as HTTP endpoints."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from agentapi.auth import create_auth_dependency
from agentapi.config import load_config
from agentapi.limiter import create_rate_limit_dependency
from agentapi.logger import RequestLogger
from agentapi.models import AgentConfig, ServerConfig
from agentapi.wrapper import execute_agent

# ---------------------------------------------------------------------------
# Web UI HTML
# ---------------------------------------------------------------------------
_WEB_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  h1 {{ color: #38bdf8; margin-bottom: .25rem; }}
  .sub {{ color: #94a3b8; margin-bottom: 2rem; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px;
           padding: 1.5rem; margin-bottom: 1.5rem; }}
  .card h2 {{ font-size: 1.1rem; color: #7dd3fc; margin-bottom: .5rem; }}
  .card p {{ font-size: .9rem; color: #94a3b8; }}
  label {{ display: block; margin-top: .75rem; font-size: .85rem; color: #cbd5e1; }}
  textarea {{ width: 100%; margin-top: .25rem; padding: .75rem; border-radius: 8px;
              border: 1px solid #334155; background: #0f172a; color: #e2e8f0;
              font-family: monospace; font-size: .9rem; resize: vertical; }}
  .row {{ display: flex; gap: .75rem; align-items: center; margin-top: .75rem; }}
  button {{ padding: .6rem 1.4rem; border: none; border-radius: 8px; cursor: pointer;
            background: #0ea5e9; color: #fff; font-weight: 600; font-size: .9rem; }}
  button:hover {{ background: #0284c7; }}
  button:disabled {{ opacity: .5; cursor: not-allowed; }}
  .meta {{ font-size: .8rem; color: #64748b; margin-top: .5rem; }}
  pre {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px;
         padding: 1rem; margin-top: .5rem; overflow-x: auto; font-size: .85rem;
         color: #a5f3fc; white-space: pre-wrap; }}
  .apikey-row {{ display: flex; gap: .5rem; align-items: center; margin-bottom: 1.5rem; }}
  .apikey-row input {{ flex: 1; padding: .5rem .75rem; border-radius: 8px;
                       border: 1px solid #334155; background: #0f172a; color: #e2e8f0;
                       font-family: monospace; font-size: .85rem; }}
</style>
</head>
<body>
<h1>{name}</h1>
<p class="sub">{description}</p>

<div class="apikey-row">
  <input id="apiKey" type="text" placeholder="Enter API key (if required)" />
  <button onclick="document.getElementById('apiKey').value=''">Clear</button>
</div>

{agent_cards}

<script>
async function callAgent(path, btn) {{
  const ta = document.getElementById('ta-' + path);
  const out = document.getElementById('out-' + path);
  const meta = document.getElementById('meta-' + path);
  const input = ta.value;
  btn.disabled = true;
  btn.textContent = 'Running...';
  out.textContent = '';
  meta.textContent = '';
  const start = performance.now();
  try {{
    const apiKey = document.getElementById('apiKey').value.trim();
    const headers = {{ 'Content-Type': 'application/json' }};
    if (apiKey) headers['X-API-Key'] = apiKey;
    const resp = await fetch(path, {{
      method: 'POST',
      headers,
      body: JSON.stringify({{ input: input }}),
    }});
    const elapsed = (performance.now() - start).toFixed(0);
    const data = await resp.json();
    out.textContent = JSON.stringify(data, null, 2);
    meta.textContent = resp.status + ' | ' + elapsed + 'ms';
  }} catch (e) {{
    out.textContent = 'Error: ' + e.message;
  }}
  btn.disabled = false;
  btn.textContent = 'Run';
}}
</script>
</body>
</html>"""


def _build_agent_card(agent: AgentConfig) -> str:
    safe_path = agent.path
    return f"""
<div class="card">
  <h2>{agent.name} <span style="font-size:.8rem;color:#64748b;">POST {safe_path}</span></h2>
  <p>{agent.description or 'No description'}</p>
  <label for="ta-{safe_path}">Input (JSON)</label>
  <textarea id="ta-{safe_path}" rows="4" placeholder='{{"input": "hello"}}'></textarea>
  <div class="row">
    <button onclick="callAgent('{safe_path}', this)">Run</button>
    <span class="meta" id="meta-{safe_path}"></span>
  </div>
  <pre id="out-{safe_path}"></pre>
</div>"""


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config: ServerConfig | None = None, config_path: str | None = None) -> FastAPI:
    """Build and return the FastAPI application."""
    if config is None:
        config = load_config(config_path)

    app = FastAPI(
        title=config.name,
        description=config.description,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    auth_dep = create_auth_dependency(config.auth)
    rate_dep = create_rate_limit_dependency(config.rate_limit)
    req_logger = RequestLogger(config.database)

    # Store refs for the CLI to access
    app.state.config = config
    app.state.logger = req_logger

    # ---- Health endpoint (no auth) ----
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "name": config.name}

    # ---- Logs endpoint (requires auth) ----
    @app.get("/logs", tags=["system"], dependencies=[Depends(auth_dep)])
    async def get_logs(limit: int = 50):
        logs = req_logger.get_recent(limit)
        return [
            {
                "id": l.id,
                "timestamp": l.timestamp,
                "method": l.method,
                "path": l.path,
                "status_code": l.status_code,
                "client_ip": l.client_ip,
                "duration_ms": l.duration_ms,
                "api_key_prefix": l.api_key_prefix,
            }
            for l in logs
        ]

    # ---- Web UI at / ----
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def web_ui():
        cards = "\n".join(_build_agent_card(a) for a in config.agents)
        return _WEB_UI_HTML.format(
            name=config.name,
            description=config.description,
            agent_cards=cards,
        )

    # ---- Dynamic agent endpoints ----
    agent_map: dict[str, AgentConfig] = {}

    for agent in config.agents:
        agent_map[agent.path] = agent

        # Build the endpoint handler via closure
        def _make_handler(ac: AgentConfig):
            async def handler(
                request: Request,
                _auth: Any = Depends(auth_dep),
                _rl: Any = Depends(rate_dep),
            ):
                client_ip = request.client.host if request.client else "unknown"
                api_key = request.headers.get(config.auth.header_name, "")
                start = time.monotonic()
                status_code = 200

                try:
                    body = await request.json()
                except Exception:
                    body = {}

                try:
                    result = await execute_agent(ac, body)
                    status_code = 200 if result.get("success") else 500
                except HTTPException:
                    raise
                except Exception as exc:
                    result = {"success": False, "error": str(exc)}
                    status_code = 500

                duration_ms = (time.monotonic() - start) * 1000
                req_logger.log(
                    method="POST",
                    path=ac.path,
                    status_code=status_code,
                    client_ip=client_ip,
                    request_body=body,
                    response_body=result,
                    duration_ms=duration_ms,
                    api_key_prefix=api_key,
                )
                return JSONResponse(content=result, status_code=status_code)

            return handler

        endpoint_fn = _make_handler(agent)
        app.add_api_route(
            agent.path,
            endpoint_fn,
            methods=[agent.method],
            tags=["agents"],
            summary=agent.description or agent.name,
        )

    return app
