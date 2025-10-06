---
description: 项目结构和架构认知
---

# 项目结构和架构

## 目录结构
```
openapi-mcp/
├── openapi_mcp/           # 主要代码包
│   ├── __init__.py       # 包初始化，导出主要类
│   ├── server.py         # 核心 MCP Server 实现
│   ├── config.py         # 配置管理
│   ├── security.py       # 安全功能
│   ├── transport.py      # 传输层处理
│   ├── cache.py          # 缓存机制
│   ├── tools/            # MCP 工具实现
│   │   ├── __init__.py
│   │   ├── base.py       # 工具基类
│   │   ├── endpoints.py  # 端点相关工具
│   │   ├── models.py     # 数据模型工具
│   │   └── search.py     # 搜索功能工具
│   └── formatters/       # 输出格式化器
│       ├── __init__.py
│       ├── markdown.py   # Markdown 格式化
│       ├── json.py       # JSON 格式化
│       └── base.py       # 格式化器基类
├── tests/                # 测试文件
│   ├── __init__.py
│   ├── test_server.py    # 服务器测试
│   ├── test_config.py    # 配置测试
│   ├── test_tools/       # 工具测试
│   └── test_integration.py # 集成测试
├── examples/             # 使用示例
│   ├── mcp_inspector_test.py    # stdio 模式示例
│   └── mcp_http_example.py      # HTTP 模式示例
├── docs/                 # 文档目录
├── .claude/              # Claude 配置
│   └── memory/           # 模块化记忆
├── .cursor/              # Cursor 配置
│   └── rules/            # 编码规则
├── pyproject.toml        # 项目配置
├── README.md            # 项目说明
├── CLAUDE.md            # Claude 指导（已重构为模块化）
└── LICENSE              # MIT 许可证
```

## 核心类关系

### OpenApiMcpServer
- **位置**: `openapi_mcp/server.py`
- **功能**: 与 FastAPI 应用集成的主要服务器类
- **职责**:
  - 管理 OpenAPI schema 缓存
  - 注册和管理 MCP 工具
  - 处理 MCP 端点挂载
  - 初始化安全组件

### OpenApiMcpConfig
- **位置**: `openapi_mcp/config.py`
- **功能**: 基于 Pydantic 的配置模型
- **主要配置项**:
  - 缓存设置 (cache_ttl, cache_enabled)
  - 路由配置 (prefix, include_sse)
  - 输出格式 (output_format, max_content_length)
  - 安全设置 (allowed_tags, tool_filter)
  - CORS 配置

### 工具系统架构
- **BaseMcpTool**: 所有工具的抽象基类
- **endpoints.py**: 端点相关工具 (4个工具)
- **models.py**: 数据模型工具 (2个工具)
- **search.py**: 搜索功能工具 (2个工具)
- **认证和示例**: 1个工具

## 传输层架构

### 支持的协议
- **JSON-RPC 2.0**: 标准 MCP 协议，通过 POST 请求
- **Server-Sent Events (SSE)**: 实时推送，通过 GET 请求
- **会话管理**: 通过 DELETE 请求清理会话

### 请求路由
- **POST /mcp**: JSON-RPC 工具调用
- **GET /mcp**: SSE 连接和实时数据
- **DELETE /mcp**: 会话清理

## 安全架构

### 三层安全机制
1. **工具过滤** (`ToolFilter`): 根据路径模式、标签或自定义逻辑过滤端点
2. **数据脱敏** (`SensitiveDataMasker`): 在响应中脱敏敏感信息
3. **访问日志** (`AccessLogger`): 记录访问日志，可选数据脱敏

### 配置安全
```python
config = OpenApiMcpConfig(
    allowed_tags=["public", "api"],  # 只暴露特定标签
    tool_filter=lambda path, method, info: not path.startswith("/admin"),
    enable_masking=True,
    enable_logging=True
)
```

## 缓存策略

### 缓存层级
- **OpenAPI Schema 缓存**: 缓存解析后的 OpenAPI 规范
- **工具结果缓存**: 缓存工具执行结果（可选）
- **配置缓存**: 缓存配置验证结果

### 缓存失效
- 手动失效: `mcp_server.invalidate_cache()`
- 自动失效: 基于 TTL 配置
- 智能失效: 检测 FastAPI 应用变更

## 扩展机制

### 自定义工具
```python
from openapi_mcp.tools.base import BaseMcpTool

class CustomTool(BaseMcpTool):
    name = 'custom_analysis'
    description = '自定义分析工具'

    async def execute(self, **kwargs):
        # 自定义逻辑
        pass
```

### 自定义格式化器
```python
from openapi_mcp.formatters.base import BaseFormatter

class CustomFormatter(BaseFormatter):
    def format(self, data: Any) -> str:
        # 自定义格式化逻辑
        return formatted_string
```

## 依赖关系

### 核心依赖
- **FastAPI**: Web 框架，提供 OpenAPI 支持
- **MCP**: Model Context Protocol SDK
- **Pydantic**: 数据验证和配置管理

### 开发依赖
- **pytest**: 测试框架，支持 asyncio
- **ruff**: 代码格式化和检查
- **basedpyright**: 严格类型检查
- **uvicorn**: ASGI 服务器（开发/测试）