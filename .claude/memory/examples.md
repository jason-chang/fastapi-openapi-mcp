---
description: 使用示例和集成模式
---

# 使用示例和集成模式

## 基础集成示例

### 最简单的集成
```python
# basic_integration.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer

app = FastAPI(title="My API", version="1.0.0")

@app.get("/users")
async def list_users():
    return {"users": []}

# 一行代码集成 MCP
mcp_server = OpenApiMcpServer(app)
mcp_server.mount("/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 自定义配置集成
```python
# custom_config.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig

app = FastAPI(title="E-commerce API", version="1.0.0")

# 自定义 MCP 配置
config = OpenApiMcpConfig(
    cache_ttl=600,                    # 10分钟缓存
    output_format="markdown",         # Markdown 输出格式
    max_content_length=2000,          # 限制内容长度
    allowed_tags=["public", "api"],   # 只暴露特定标签
    enable_masking=True,              # 启用数据脱敏
    enable_logging=True               # 启用访问日志
)

mcp_server = OpenApiMcpServer(app, config)
mcp_server.mount("/api-mcp")  # 自定义路径

# 添加路由
@app.get("/products", tags=["products"])
async def list_products():
    return {"products": []}

@app.get("/admin/users", tags=["admin"])  # 不会被暴露，因为不在 allowed_tags 中
async def admin_users():
    return {"admin_users": []}
```

## 高级集成模式

### 多应用实例
```python
# multi_app.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig

# 公共 API
public_app = FastAPI(title="Public API", version="1.0.0")

@public_app.get("/products", tags=["public"])
async def public_products():
    return {"products": []}

# 内部 API
internal_app = FastAPI(title="Internal API", version="1.0.0")

@internal_app.get("/analytics", tags=["internal"])
async def analytics():
    return {"analytics": []}

# 分别配置 MCP 服务器
public_config = OpenApiMcpConfig(
    allowed_tags=["public"],
    output_format="markdown"
)

internal_config = OpenApiMcpConfig(
    allowed_tags=["internal"],
    output_format="json",
    enable_masking=True
)

public_mcp = OpenApiMcpServer(public_app, public_config)
internal_mcp = OpenApiMcpServer(internal_app, internal_config)

# 挂载到不同路径
public_mcp.mount("/public-mcp")
internal_mcp.mount("/internal-mcp")
```

### 自定义工具集成
```python
# custom_tools.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig
from openapi_mcp.tools.base import BaseMcpTool
from mcp.types import CallToolResult, TextContent
import asyncio

class ApiHealthTool(BaseMcpTool):
    """自定义 API 健康检查工具"""

    name = "api_health_check"
    description = "检查 API 服务的健康状态"

    async def execute(self, **kwargs) -> CallToolResult:
        """执行健康检查"""
        # 获取 FastAPI 应用实例
        app = self.server.app

        # 执行健康检查逻辑
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "endpoints_count": len(app.routes),
            "openapi_version": app.openapi().get("openapi", "unknown")
        }

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"# API 健康状态\n\n{json.dumps(health_status, indent=2)}"
            )]
        )

class ApiMetricsTool(BaseMcpTool):
    """自定义 API 指标工具"""

    name = "api_metrics"
    description = "获取 API 使用指标"

    async def execute(self, **kwargs) -> CallToolResult:
        """获取 API 指标"""
        # 这里可以集成真实的指标收集系统
        metrics = {
            "total_requests": 1000,
            "avg_response_time": 150,
            "error_rate": 0.02,
            "top_endpoints": [
                {"endpoint": "/products", "requests": 300},
                {"endpoint": "/users", "requests": 250}
            ]
        }

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"# API 使用指标\n\n```json\n{json.dumps(metrics, indent=2)}\n```"
            )]
        )

# 使用自定义工具
app = FastAPI(title="Analytics API", version="1.0.0")

config = OpenApiMcpConfig(
    custom_tools=[ApiHealthTool(), ApiMetricsTool()]
)

mcp_server = OpenApiMcpServer(app, config)
mcp_server.mount("/mcp-with-custom-tools")
```

### 安全过滤配置
```python
# security_config.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig

app = FastAPI(title="Secure API", version="1.0.0")

# 敏感信息脱敏模式
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
    r'token["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
    r'api_key["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 信用卡号
    r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'           # SSN
]

def advanced_tool_filter(path: str, method: str, endpoint_info: dict) -> bool:
    """高级工具过滤器"""
    # 过滤管理端点
    if path.startswith("/admin/") or path.startswith("/internal/"):
        return False

    # 过滤敏感操作
    if method.upper() in ["DELETE", "PATCH"] and "user" in path.lower():
        return False

    # 过滤调试端点
    if "debug" in path.lower() or "trace" in path.lower():
        return False

    # 只允许特定标签
    allowed_tags = endpoint_info.get("tags", [])
    if not any(tag in ["public", "api", "v1"] for tag in allowed_tags):
        return False

    return True

config = OpenApiMcpConfig(
    tool_filter=advanced_tool_filter,
    enable_masking=True,
    sensitive_patterns=SENSITIVE_PATTERNS,
    enable_logging=True,
    allowed_origins=["https://myapp.com", "https://admin.myapp.com"]
)

mcp_server = OpenApiMcpServer(app, config)
mcp_server.mount("/secure-mcp")
```

## 测试和调试示例

### 开发环境测试
```python
# dev_test.py
import asyncio
import json
from examples.mcp_http_example import create_sample_api, create_mcp_server

async def test_mcp_tools():
    """测试 MCP 工具功能"""

    # 创建测试应用
    app = create_sample_api()
    server = create_mcp_server(app)

    print("🧪 测试 MCP 工具...")

    # 测试列出工具
    tools = await server.list_tools()
    print(f"✅ 发现 {len(tools)} 个工具:")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")

    # 测试执行工具
    print("\n🔧 测试工具执行:")

    # 测试列出端点
    result = await server.execute_tool("list_openapi_endpoints")
    print(f"✅ list_openapi_endpoints: {len(result.content[0].text)} 字符")

    # 测试按标签搜索
    result = await server.execute_tool("search_endpoints_by_tag", {"tag": "products"})
    print(f"✅ search_endpoints_by_tag: 找到商品相关端点")

    # 测试关键词搜索
    result = await server.execute_tool("search_endpoints", {"keyword": "user"})
    print(f"✅ search_endpoints: 找到用户相关端点")

    # 测试获取标签列表
    result = await server.execute_tool("get_tags_list")
    print(f"✅ get_tags_list: 获取标签列表成功")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
```

### 性能基准测试
```python
# benchmark.py
import asyncio
import time
from examples.mcp_http_example import create_sample_api, create_mcp_server

async def benchmark_tools():
    """工具性能基准测试"""

    app = create_sample_api()
    server = create_mcp_server(app)

    # 预热
    await server.list_tools()

    # 基准测试
    test_cases = [
        ("list_openapi_endpoints", {}),
        ("search_endpoints_by_tag", {"tag": "products"}),
        ("search_endpoints", {"keyword": "product"}),
        ("get_tags_list", {}),
        ("get_api_models", {}),
    ]

    print("📊 性能基准测试:")
    print(f"{'工具名称':<25} {'平均耗时(ms)':<15} {'QPS':<10}")
    print("-" * 50)

    for tool_name, args in test_cases:
        # 执行多次测试
        times = []
        for _ in range(10):
            start = time.time()
            await server.execute_tool(tool_name, args)
            end = time.time()
            times.append((end - start) * 1000)

        avg_time = sum(times) / len(times)
        qps = 1000 / avg_time

        print(f"{tool_name:<25} {avg_time:<15.2f} {qps:<10.2f}")

if __name__ == "__main__":
    asyncio.run(benchmark_tools())
```

## 部署示例

### Docker 部署
```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --frozen

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_CACHE_TTL=600
      - MCP_OUTPUT_FORMAT=markdown
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### 生产环境配置
```python
# production.py
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig
import os

app = FastAPI(
    title="Production API",
    version="1.0.0",
    docs_url=None,  # 生产环境关闭文档
    redoc_url=None
)

# 生产环境配置
config = OpenApiMcpConfig(
    cache_ttl=int(os.getenv("MCP_CACHE_TTL", "1800")),  # 30分钟
    output_format=os.getenv("MCP_OUTPUT_FORMAT", "json"),
    max_content_length=int(os.getenv("MCP_MAX_LENGTH", "5000")),
    enable_logging=True,
    enable_masking=True,
    allowed_origins=os.getenv("MCP_ALLOWED_ORIGINS", "").split(","),
    tool_filter=lambda path, method, info: not path.startswith("/internal/")
)

mcp_server = OpenApiMcpServer(app, config)
mcp_server.mount("/mcp")

# 添加监控端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return {
        "mcp_tools_count": len(mcp_server.tools),
        "cache_hits": mcp_server.cache.get_stats().get("hits", 0),
        "uptime": "..."  # 实际实现中应该计算真实的运行时间
    }
```

## 集成测试示例

### 端到端测试
```python
# e2e_test.py
import asyncio
import httpx
import json

async def test_e2e_mcp_workflow():
    """端到端 MCP 工作流测试"""

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🔄 测试 MCP 端到端工作流...")

        # 1. 初始化会话
        init_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
        )
        assert init_response.status_code == 200
        print("✅ 会话初始化成功")

        # 2. 列出工具
        tools_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
        )
        assert tools_response.status_code == 200
        tools = tools_response.json()["result"]["tools"]
        print(f"✅ 获取到 {len(tools)} 个工具")

        # 3. 执行工具链
        workflow_steps = [
            ("list_openapi_endpoints", {}),
            ("get_tags_list", {}),
            ("search_endpoints_by_tag", {"tag": "products"}),
            ("get_api_models", {}),
        ]

        for step_num, (tool_name, args) in enumerate(workflow_steps, 1):
            response = await client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": step_num + 2,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": args}
                }
            )

            assert response.status_code == 200
            result = response.json()
            print(f"✅ 步骤 {step_num}: {tool_name} 执行成功")

        # 4. 清理会话
        delete_response = await client.delete(f"{base_url}/mcp")
        print(f"✅ 会话清理完成: {delete_response.status_code}")

        print("🎉 端到端测试完成！")

if __name__ == "__main__":
    asyncio.run(test_e2e_mcp_workflow())
```

这些示例涵盖了从基础集成到高级部署的各种场景，为不同需求的用户提供了完整的参考。