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

| Status | Tool 名称 | 描述 |
|--------|------|------|
| ⭐ | `list_openapi_endpoints` | 列出所有 API 接口（按标签分组） |
| ⭐ | `get_endpoint_details` | 获取接口详细信息（含认证、示例、废弃状态） |
| ⭐ | `search_endpoints_by_tag` | 按标签搜索接口 |
| ⭐ | `get_api_models` | 获取数据模型列表摘要 |
| ⭐ | `get_model_details` | 获取单个模型的完整定义（含引用解析） |
| ⭐ | `search_endpoints` | 关键词搜索接口（路径、摘要、描述） |
| ⭐ | `get_auth_requirements` | 查询接口的认证要求 |
| ⭐ | `get_endpoint_examples` | 获取接口的请求/响应示例 |
| ⭐ | `get_tags_list` | 列出所有可用的标签及描述 |

### 访问方式

- ✅ **JSON-RPC 2.0** - 标准 MCP 协议
- ✅ **Server-Sent Events (SSE)** - 实时推送
- ✅ **REST API** - 便于调试和测试

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
npx @modelcontextprotocol/inspector uv run python examples/mcp_inspector_test.py
```

这会打开一个 Web 界面（`http://localhost:5173`），让你可以：
- ✅ 查看所有 9 个 MCP 工具
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
    prefix='/api-mcp',
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

## 📋 开发计划

### 阶段一：核心 Library 开发（3-4 天）

#### 1.1 项目基础搭建
- [x] 创建项目目录结构
- [x] 编写 README.md
- [ ] 配置 `pyproject.toml`
- [ ] 设置代码规范（ruff, basedpyright）
- [ ] 初始化测试框架

#### 1.2 实现高优先级 Tools
- [ ] 迁移 `list_openapi_endpoints`
- [ ] 增强 `get_endpoint_details`
  - [ ] 添加认证要求字段
  - [ ] 添加请求/响应示例
  - [ ] 标注废弃状态
- [ ] 迁移 `search_endpoints_by_tag`
- [ ] 优化 `get_api_models`（只返回摘要）
- [ ] 新增 `get_model_details`
  - [ ] 解析字段定义
  - [ ] 解析 `$ref` 引用
  - [ ] 显示验证规则
- [ ] 新增 `search_endpoints`
  - [ ] 路径模糊匹配
  - [ ] 关键词搜索

#### 1.3 实现中优先级 Tools
- [ ] 新增 `get_auth_requirements`
- [ ] 新增 `get_endpoint_examples`
- [ ] 新增 `get_tags_list`

### 阶段二：增强功能（2 天）

#### 2.1 缓存机制
- [ ] 实现 OpenAPI schema 缓存
- [ ] 支持缓存过期时间
- [ ] 提供手动清除缓存接口

#### 2.2 扩展系统
- [ ] 定义 Tool 基类
- [ ] 支持自定义 Tools
- [ ] Tool 注册机制

#### 2.3 安全和过滤
- [ ] 工具过滤器实现
- [ ] 敏感信息脱敏
- [ ] 访问日志

#### 2.4 输出格式化
- [ ] Markdown 格式化器
- [ ] JSON 格式化器
- [ ] Plain text 格式化器
- [ ] 输出长度限制

### 阶段三：文档和发布（2 天）

#### 3.1 文档完善
- [ ] API 文档
- [ ] 集成示例（FastAPI）
- [ ] 最佳实践指南
- [ ] 常见问题 FAQ

#### 3.2 测试
- [ ] 单元测试（覆盖率 > 80%）
- [ ] 集成测试
- [ ] 示例项目测试
- [ ] 性能测试

#### 3.3 发布准备
- [ ] 版本号规范（Semantic Versioning）
- [ ] CHANGELOG.md
- [ ] LICENSE
- [ ] GitHub CI/CD
- [ ] PyPI 发布配置

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

#### `list_openapi_endpoints`

列出所有 API 接口，按标签分组显示。

**参数**: 无

**返回示例**:
```markdown
🚀 **Available API Endpoints:**

## 📁 Users
- **GET** `/api/v1/users` - List all users
- **POST** `/api/v1/users` - Create new user

## 📁 Items
- **GET** `/api/v1/items` - List all items

📊 **Total endpoints:** 3
```

#### `get_endpoint_details`

获取指定接口的详细信息。

**参数**:
- `path` (string, required): 接口路径，例如 `/api/v1/users`
- `method` (string, required): HTTP 方法，例如 `GET`

**返回**: 包含参数、请求体、响应、认证要求、示例等完整信息

#### `search_endpoints`

通过关键词搜索接口。

**参数**:
- `keyword` (string, required): 搜索关键词
- `search_in` (string, optional): 搜索范围 - `path`, `summary`, `description`, `all` (默认)

**返回**: 匹配的接口列表

#### `get_model_details`

获取数据模型的完整定义。

**参数**:
- `model_name` (string, required): 模型名称

**返回**: 模型的所有字段、类型、验证规则、引用关系等

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
