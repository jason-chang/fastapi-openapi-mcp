---
description: 常见问题和故障排除
---

# 故障排除指南

## 常见启动问题

### 依赖安装失败
```bash
# 问题：uv sync 失败
# 解决方案：
uv cache clean  # 清理缓存
uv sync --reinstall  # 重新安装

# 如果仍有问题，检查 Python 版本
python --version  # 需要 3.13+
```

### 导入错误
```python
# 问题：ImportError: cannot import name 'OpenApiMcpServer'
# 解决方案：检查是否在正确的虚拟环境中
uv run python -c "from openapi_mcp import OpenApiMcpServer; print('导入成功')"
```

## MCP Inspector 问题

### Inspector 无法连接
```bash
# 问题：MCP Inspector 显示连接失败
# 检查清单：
1. 确保 npx @modelcontextprotocol/inspector 已安装
2. 检查示例文件语法是否正确
3. 验证 stdio 输出格式

# 调试命令：
uv run python examples/mcp_inspector_test.py 2>&1 | head -20
```

### 工具列表为空
```python
# 问题：Inspector 中没有显示工具
# 可能原因：
1. FastAPI 应用没有正确配置 OpenAPI
2. 工具过滤器过于严格
3. 缓存问题

# 调试代码：
import json
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer

app = FastAPI()
server = OpenApiMcpServer(app)
print("OpenAPI spec keys:", list(app.openapi().keys()))
print("注册的工具数量:", len(server.tools))
```

## HTTP 模式问题

### 服务器启动失败
```bash
# 问题：端口被占用
lsof -ti:8000 | xargs kill -9  # 杀死占用端口的进程

# 问题：权限不足
# 使用非特权端口（>1024）
uv run python -c "
from examples.mcp_http_example import create_sample_api, create_mcp_server
import uvicorn

app = create_sample_api()
server = create_mcp_server(app)
server.mount('/mcp')
uvicorn.run(app, host='127.0.0.1', port=8080)  # 使用 8080 端口
"
```

### MCP 端点无响应
```bash
# 测试 MCP 端点是否工作
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'

# 检查服务器日志
tail -f /tmp/uvicorn.log
```

## 测试问题

### 测试失败
```bash
# 问题：pytest 测试失败
# 调试步骤：

1. 运行特定测试文件并显示详细输出
uv run pytest tests/test_server.py -v -s

2. 检查测试覆盖率
uv run pytest --cov=openapi_mcp --cov-report=html

3. 运行特定测试函数
uv run pytest tests/test_server.py::TestOpenApiMcpServer::test_list_tools -v
```

### 异步测试问题
```python
# 问题：异步测试挂起
# 解决方案：确保使用 pytest-asyncio
uv add --dev pytest-asyncio

# 在测试文件中添加：
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## 性能问题

### 响应缓慢
```python
# 问题：工具执行缓慢
# 诊断步骤：

1. 检查缓存配置
config = OpenApiMcpConfig(cache_ttl=300)  # 5分钟缓存

2. 启用性能日志
import logging
logging.basicConfig(level=logging.DEBUG)

3. 监控内存使用
import psutil
print(f"内存使用: {psutil.virtual_memory().percent}%")
```

### 内存泄漏
```bash
# 监控内存使用
uv run python -c "
import psutil
import time
from openapi_mcp import OpenApiMcpServer
from fastapi import FastAPI

app = FastAPI()
server = OpenApiMcpServer(app)

for i in range(10):
    print(f'迭代 {i}: 内存使用 {psutil.virtual_memory().percent}%')
    # 执行一些操作
    await server.list_tools()
    time.sleep(1)
"
```

## 配置问题

### Pydantic 验证错误
```python
# 问题：配置验证失败
# 常见错误和解决方案：

1. cache_ttl 必须是正整数
config = OpenApiMcpConfig(cache_ttl=300)  # ✅ 正确
config = OpenApiMcpConfig(cache_ttl=-1)   # ❌ 错误

2. allowed_tags 必须是列表
config = OpenApiMcpConfig(allowed_tags=['users', 'products'])  # ✅ 正确
config = OpenApiMcpConfig(allowed_tags='users')               # ❌ 错误

3. output_format 必须是有效值
config = OpenApiMcpConfig(output_format='markdown')  # ✅ 正确
config = OpenApiMcpConfig(output_format='invalid')   # ❌ 错误
```

### FastAPI 集成问题
```python
# 问题：MCP 服务器挂载失败
# 检查清单：

1. 确保 FastAPI 应用有 OpenAPI 规范
from fastapi import FastAPI
app = FastAPI(title="My API", version="1.0.0")  # 必须有 title 和 version

2. 检查路径冲突
mcp_server.mount('/mcp')  # 确保这个路径没有被其他路由使用

3. 验证应用状态
print(app.openapi())  # 应该返回有效的 OpenAPI 规范
```

## 调试技巧

### 启用详细日志
```python
import logging
import structlog

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structdev.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### 使用调试断点
```python
# 在关键位置添加调试断点
import pdb

async def debug_tool_execution(self, tool_name: str, **kwargs):
    """调试工具执行过程。"""
    pdb.set_trace()  # 在这里暂停执行

    tool = self.get_tool(tool_name)
    print(f"工具: {tool.name}")
    print(f"参数: {kwargs}")

    result = await tool.execute(**kwargs)
    print(f"结果类型: {type(result)}")

    return result
```

### 检查 MCP 协议消息
```python
# 添加 MCP 消息日志
import json

def log_mcp_message(message_type: str, data: dict):
    """记录 MCP 协议消息。"""
    print(f"[MCP] {message_type}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

# 在传输处理器中使用
async def handle_request(self, request):
    log_mcp_message("REQUEST", request)
    # ... 处理请求
    log_mcp_message("RESPONSE", response)
```

## 获取帮助

### 收集诊断信息
```bash
# 收集系统信息
echo "=== Python 版本 ==="
python --version

echo "=== 依赖版本 ==="
uv pip list | grep -E "(fastapi|mcp|pydantic)"

echo "=== 项目配置 ==="
cat pyproject.toml

echo "=== 测试状态 ==="
uv run pytest --tb=short --maxfail=1
```

### 报告问题时包含的信息
1. **错误消息**: 完整的错误堆栈跟踪
2. **重现步骤**: 详细的操作步骤
3. **环境信息**: Python 版本、操作系统、依赖版本
4. **配置**: 相关的配置代码
5. **期望行为**: 描述您期望发生什么
6. **实际行为**: 描述实际发生了什么

### 有用的调试命令
```bash
# 检查 Python 路径
uv run python -c "import sys; print('\n'.join(sys.path))"

# 验证模块导入
uv run python -c "import openapi_mcp; print(openapi_mcp.__file__)"

# 测试基本功能
uv run python -c "
from fastapi import FastAPI
from openapi_mcp import OpenApiMcpServer
app = FastAPI()
server = OpenApiMcpServer(app)
print(f'工具数量: {len(server.tools)}')
"
```