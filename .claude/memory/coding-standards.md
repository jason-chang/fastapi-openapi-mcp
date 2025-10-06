---
description: 编码规范和最佳实践
---

# 编码规范和最佳实践

## 代码风格

### Python 版本要求
- **Python 3.13+** - 使用最新语言特性
- 现代化的类型注解系统
- 全程 async/await 模式

### 代码格式化
```bash
# 格式化代码
uv run ruff format .

# 检查并自动修复
uv run ruff check . --fix
```

### 类型检查
```bash
# 严格类型检查
uv run basedpyright
```

## 命名约定

### 文件和目录
- **模块名**: `snake_case.py` (例: `openapi_mcp_server.py`)
- **包名**: `snake_case` (例: `openapi_mcp/`)
- **类名**: `PascalCase` (例: `OpenApiMcpServer`)

### 变量和函数
- **变量**: `snake_case` (例: `cache_ttl`, `api_endpoints`)
- **函数**: `snake_case` (例: `get_endpoint_details()`)
- **私有成员**: 前缀下划线 (例: `_validate_config()`)

### 常量
- **常量**: `UPPER_SNAKE_CASE` (例: `DEFAULT_CACHE_TTL`)
- **枚举**: `PascalCase` (例: `OutputFormat.Markdown`)

## 文档字符串

### 使用 Google 风格
```python
async def get_endpoint_details(
    self,
    path: str,
    method: str,
    include_examples: bool = True
) -> EndpointDetails:
    """获取端点详细信息。

    Args:
        path: API 端点路径，例如 '/api/v1/users'
        method: HTTP 方法，例如 'GET', 'POST'
        include_examples: 是否包含请求/响应示例

    Returns:
        包含端点详细信息的 EndpointDetails 对象

    Raises:
        ValueError: 当路径或方法无效时
        KeyError: 当端点不存在时

    Example:
        >>> details = await server.get_endpoint_details('/users', 'GET')
        >>> print(details.description)
        '获取用户列表'
    """
```

## 类型注解规范

### 完整类型注解
```python
# ✅ 好的示例：完整类型注解
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

def process_endpoints(
    endpoints: List[Dict[str, Any]],
    filters: Optional[Dict[str, str]] = None
) -> Dict[str, Union[str, List[str]]]:
    """处理端点列表并返回过滤结果。"""
    pass

# ❌ 避免：缺少类型注解
def process_endpoints(endpoints, filters=None):
    pass
```

### 复杂类型使用 TypeAlias
```python
from typing import TypeAlias, Dict, List, Optional

# 定义类型别名
EndpointInfo: TypeAlias = Dict[str, Any]
FilterConfig: TypeAlias = Optional[Dict[str, str]]
ToolResult: TypeAlias = Dict[str, Union[str, List[str]]]
```

## 异步编程规范

### 统一使用 async/await
```python
# ✅ 正确：异步函数
async def fetch_openapi_spec(self) -> Dict[str, Any]:
    """获取 OpenAPI 规范。"""
    response = await self.client.get("/openapi.json")
    return response.json()

# ✅ 正确：调用异步函数
async def main():
    spec = await server.fetch_openapi_spec()
    return spec
```

### 异步上下文管理器
```python
# ✅ 正确：使用异步上下文管理器
async def with_database(self):
    """使用数据库连接。"""
    async with self.db_pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM endpoints")
        return result
```

## 错误处理

### 自定义异常类
```python
class OpenApiMcpError(Exception):
    """基础异常类。"""
    pass

class ConfigurationError(OpenApiMcpError):
    """配置错误。"""
    pass

class ToolExecutionError(OpenApiMcpError):
    """工具执行错误。"""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"工具 '{tool_name}' 执行失败: {message}")
```

### 错误处理模式
```python
# ✅ 好的错误处理
async def execute_tool(self, name: str, **kwargs) -> Any:
    """执行工具并处理错误。"""
    try:
        tool = self.get_tool(name)
        return await tool.execute(**kwargs)
    except ToolExecutionError as e:
        logger.error(f"工具执行失败: {e}")
        raise
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        raise ToolExecutionError(name, f"未预期的错误: {e}")
```

## 测试规范

### 测试文件命名
- **单元测试**: `test_{module_name}.py` (例: `test_server.py`)
- **集成测试**: `test_integration.py`
- **功能测试**: `test_{feature}_integration.py`

### 测试结构
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestOpenApiMcpServer:
    """OpenApiMcpServer 测试类。"""

    @pytest.fixture
    async def server(self):
        """创建测试服务器实例。"""
        app = create_test_app()
        return OpenApiMcpServer(app)

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """测试列出工具。"""
        tools = await server.list_tools()
        assert len(tools) > 0
        assert all(tool.name for tool in tools)

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_name(self, server):
        """测试执行无效工具名称。"""
        with pytest.raises(ValueError, match="未找到工具"):
            await server.execute_tool("invalid_tool")
```

## 性能优化

### 缓存策略
```python
# ✅ 好的缓存实现
from functools import lru_cache
from typing import Optional

class OpenApiMcpServer:
    @lru_cache(maxsize=128)
    def _get_cached_schema(self, cache_key: str) -> Optional[Dict]:
        """获取缓存的 schema。"""
        return self.cache.get(cache_key)

    async def get_endpoints(self, force_refresh: bool = False) -> List[Dict]:
        """获取端点列表，支持缓存。"""
        cache_key = "endpoints_list"
        if not force_refresh:
            cached = self._get_cached_schema(cache_key)
            if cached:
                return cached

        # 重新获取并缓存
        endpoints = await self._fetch_endpoints()
        self.cache.set(cache_key, endpoints, ttl=self.config.cache_ttl)
        return endpoints
```

### 异步并发
```python
# ✅ 好的并发处理
import asyncio

async def fetch_multiple_resources(self, urls: List[str]) -> List[Dict]:
    """并发获取多个资源。"""
    tasks = [self._fetch_single_resource(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常结果
    successful_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"获取资源失败: {result}")
        else:
            successful_results.append(result)

    return successful_results
```

## 安全编码实践

### 输入验证
```python
from pydantic import BaseModel, validator

class ToolRequest(BaseModel):
    """工具请求模型。"""
    tool_name: str
    arguments: Dict[str, Any] = {}

    @validator('tool_name')
    def validate_tool_name(cls, v):
        """验证工具名称。"""
        if not v or not v.isidentifier():
            raise ValueError('工具名称无效')
        return v
```

### 敏感数据处理
```python
class SensitiveDataMasker:
    """敏感数据脱敏器。"""

    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret',
        'credit_card', 'ssn', 'email', 'phone'
    }

    def mask_sensitive_data(self, data: Dict) -> Dict:
        """脱敏敏感数据。"""
        if isinstance(data, dict):
            return {
                k: '***' if k.lower() in self.SENSITIVE_FIELDS
                else self.mask_sensitive_data(v)
                for k, v in data.items()
            }
        return data
```

## 日志记录

### 结构化日志
```python
import structlog

logger = structlog.get_logger()

async def execute_tool(self, name: str, **kwargs) -> Any:
    """执行工具并记录结构化日志。"""
    logger.info(
        "开始执行工具",
        tool_name=name,
        arguments=list(kwargs.keys()),
        execution_id=self.generate_execution_id()
    )

    try:
        result = await self._execute_tool_internal(name, **kwargs)
        logger.info(
            "工具执行成功",
            tool_name=name,
            result_type=type(result).__name__
        )
        return result
    except Exception as e:
        logger.error(
            "工具执行失败",
            tool_name=name,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```