# FastAPI OpenAPI MCP Server

> 🚀 将 FastAPI 应用的 OpenAPI 文档转换为 MCP (Model Context Protocol) Tools，让 AI 编程助手能够高效查询 API 信息，减少 Token 消耗。

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 📖 项目简介

FastAPI OpenAPI MCP Server 是一个用于 FastAPI 应用的 MCP 服务器实现，它能够将 OpenAPI 文档转换为一系列可查询的 Tools，让 AI 编程助手（如 Claude、GPT 等）能够：

- 🎯 **按需查询** - 无需每次加载完整的 `openapi.json`
- 🔍 **精准定位** - 通过标签、路径、关键词快速找到目标接口
- 📊 **结构化信息** - 获取格式化的、易于理解的 API 信息
- 💰 **节省 Token** - 显著减少 AI 编程过程中的 Token 消耗

### 适用场景

- ✅ API 接口数量 > 30 个
- ✅ 需要 AI 辅助开发和调试
- ✅ 希望减少 AI 上下文 Token 消耗
- ✅ 需要跨项目复用 MCP 功能

## ✨ 核心功能

### MCP Tools

// TODO

### MCP Tools

// TODO

### 访问方式

- ✅ **JSON-RPC 2.0** - 标准 MCP 协议
- ✅ **Streamable HTTP** - 流式 HTTP

## 🏗️ 架构设计

### 目录结构

```
openapi-mcp-server/
│── openapi_mcp/
│   ├── __init__.py
│   ├── server.py          # 核心 MCP Server
│   ├── config.py      # 配置管理
│   ├── tools/         # Tools 实现
│   │   ├── __init__.py
|   │   ├── base.py        # Tool 基类
|   │   ├── endpoints.py   # 接口相关 tools
|   │   ├── models.py      # 模型相关 tools
|   │   └── search.py      # 搜索相关 tools
|   ├── formatters/        # 输出格式化
|   │   ├── __init__.py
|   │   ├── markdown.py    # Markdown 格式
|   │   └── json.py        # JSON 格式
|   └── cache.py           # 缓存机制
├── tests/                     # 测试文件
├── examples/                  # 使用示例
│   └── fastapi_integration.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### 核心组件

#### 1. OpenApiMcpServer

```python
class OpenApiMcpServer:
    """OpenAPI MCP Server 主类"""

    def __init__(
        self,
        fastapi_app: FastAPI,
        config: OpenApiMcpConfig | None = None
    ):
        """初始化 MCP Server

        Args:
            fastapi_app: FastAPI 应用实例
            config: 配置对象（可选）
        """
```

#### 2. OpenApiMcpConfig

```python
class OpenApiMcpConfig:
    """MCP Server 配置"""

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5分钟

    # 路由配置
    prefix: str = '/openapi-mcp'
    include_sse: bool = True
    include_rest_api: bool = True  # 调试用的 REST API

    # 输出格式
    output_format: str = 'markdown'  # markdown | json | plain
    max_output_length: int = 10000  # 防止输出过长

    # 自定义扩展
    custom_tools: list[Tool] = []
    tool_filter: Callable | None = None  # 过滤哪些接口暴露

    # 安全配置
    auth_required: bool = False
    allowed_origins: list[str] = ['*']
```

## 🚀 快速开始

### 安装

```bash
# 从 PyPI 安装（TODO: 发布后）
pip install fastapi-openapi-mcp

# 或使用 uv
uv add fastapi-openapi-mcp

# 开发模式安装
git clone https://github.com/yourusername/openapi-mcp-server.git
cd openapi-mcp-server
uv sync
```

### 💡 立即测试（使用 MCP Inspector）

在开发模式下，你可以立即使用 MCP Inspector 测试：

```bash
# 确保已安装依赖
uv sync

# 使用 MCP Inspector 测试
npx @modelcontextprotocol/inspector uv run python examples/mcp_stdio_example.py
```

这会打开一个 Web 界面（`http://localhost:5173`），让你可以：
- ✅ 查看所有 MCP Tools 和 Resources
- ✅ 交互式调用工具
- ✅ 实时查看返回结果

详细指南：[QUICKSTART_INSPECTOR.md](QUICKSTART_INSPECTOR.md)

### 基础使用

```python
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer

# 创建 FastAPI 应用
app = FastAPI(
    title="My Awesome API",
    version="1.0.0"
)

# 添加你的路由
@app.get("/users")
async def list_users():
    return {"users": []}

# 集成 MCP Server（仅需 1 行代码）
mcp_server = OpenApiMcpServer(app)
mcp_server.mount("/mcp")

# 启动应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 自定义配置

```python
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig

# 自定义配置
config = OpenApiMcpConfig(
    cache_enabled=True,
    cache_ttl=600,  # 10分钟缓存
    prefix='/openapi-mcp',
    output_format='markdown',
)

mcp_server = OpenApiMcpServer(app, config=config)
mcp_server.mount()
```

### 工具过滤（安全）

```python
def tool_filter(path: str, method: str, endpoint_info: dict) -> bool:
    """过滤不想暴露给 AI 的接口"""
    # 过滤内部接口
    if path.startswith('/internal/'):
        return False
    # 过滤管理员接口
    if 'admin' in endpoint_info.get('tags', []):
        return False
    return True

config = OpenApiMcpConfig(tool_filter=tool_filter)
mcp_server = OpenApiMcpServer(app, config=config)
```

## 🔧 高级功能

### 缓存管理

```python
# 手动清除缓存
mcp_server.invalidate_cache()

# 禁用缓存（用于开发调试）
config = OpenApiMcpConfig(cache_enabled=False)
```

### 自定义 Tools

```python
from openapi_mcp.tools.base import BaseMcpTool
from mcp.types import CallToolResult, TextContent

class CustomTool(BaseMcpTool):
    name = 'my_custom_tool'
    description = 'My custom analysis tool'

    async def execute(self, **kwargs) -> CallToolResult:
        # 访问 OpenAPI schema
        spec = self.get_openapi_spec()

        # 自定义逻辑
        result = "Custom analysis result"

        return CallToolResult(
            content=[TextContent(type='text', text=result)]
        )

# 注册自定义工具
config = OpenApiMcpConfig(custom_tools=[CustomTool()])
mcp_server = OpenApiMcpServer(app, config=config)
```

## 📚 API 参考

### MCP Tools 详细说明

// TODO

### MCP Resources 详细说明

// TODO

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 开发环境搭建

```bash
# 克隆项目
git clone https://github.com/yourusername/openapi-mcp-server.git
cd openapi-mcp-server

# 安装依赖
uv sync

# 运行测试
uv run pytest

# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check . --fix

# 类型检查
uv run basedpyright
```

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建或工具更新
```

## 📄 许可证

[MIT License](LICENSE)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [Anthropic](https://www.anthropic.com/) - MCP 协议的创建者

## 📮 联系方式

- 问题反馈: [GitHub Issues](https://github.com/yourusername/openapi-mcp-server/issues)
- 功能建议: [GitHub Discussions](https://github.com/yourusername/openapi-mcp-server/discussions)

---

**注**: 本项目当前处于开发阶段，API 可能会有变动。欢迎提前试用并提供反馈！
