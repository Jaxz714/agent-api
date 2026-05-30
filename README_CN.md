[English](README.md) | [中文](README_CN.md)

# Agent API

将任意 AI Agent 转变为 API 服务 —— 只需一个配置文件，即可获得带认证、限流、日志和文档的即时 API。

## 功能特性

- **CLI 封装** —— 将任意命令行工具暴露为 HTTP 端点
- **Python 函数封装** —— 通过 API 直接调用 Python 函数
- **API Key 认证** —— 使用 Bearer 风格的密钥保护端点安全
- **限流** —— 基于 IP 的滑动窗口限流器
- **请求日志** —— 每次请求/响应均记录到 SQLite
- **自动生成 OpenAPI 文档**，访问 `/docs`
- **Web UI**，访问 `/` 进行交互式测试
- **健康检查**，访问 `/health`

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 生成示例配置
agentapi init

# 编辑 agent.yaml 添加你的 Agent，然后启动：
agentapi serve

# 打开 http://localhost:8000 访问 Web UI
# 打开 http://localhost:8000/docs 查看 Swagger 文档
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `agentapi init` | 创建示例 `agent.yaml` |
| `agentapi serve` | 启动 API 服务器 |
| `agentapi serve --port 9000` | 自定义端口 |
| `agentapi serve --config my.yaml` | 自定义配置文件路径 |
| `agentapi logs` | 查看最近的请求日志 |
| `agentapi keys generate` | 生成新的 API Key |
| `agentapi test /chat "hello"` | 测试端点 |

## 配置文件 (`agent.yaml`)

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

## Agent 类型

### CLI (`type: "cli"`)

运行 shell 命令。`{input}` 占位符会被替换为 JSON 序列化的请求体。

### Python (`type: "python"`)

导入模块并调用函数。函数接收请求体作为 dict 参数。

```yaml
agents:
  - name: "analyze"
    type: "python"
    module: "my_module"
    function: "analyze"
    method: "POST"
    path: "/analyze"
```

## 许可证

MIT
