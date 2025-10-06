"""
MCP Server 配置管理
"""

from collections.abc import Callable
from typing import Any

from mcp.types import Tool
from pydantic import BaseModel, ConfigDict, Field


class OpenApiMcpConfig(BaseModel):
	"""OpenAPI MCP Server 配置"""

	# 缓存配置
	cache_enabled: bool = Field(default=True, description='是否启用缓存')
	cache_ttl: int = Field(default=300, description='缓存过期时间（秒）', ge=0)

	# 路由配置
	prefix: str = Field(default='/openapi-mcp', description='MCP 路由前缀')
	include_sse: bool = Field(default=True, description='是否包含 SSE 端点')
	include_rest_api: bool = Field(
		default=True, description='是否包含 REST API（用于调试）'
	)

	# 输出格式配置
	output_format: str = Field(
		default='markdown', description='输出格式', pattern='^(markdown|json|plain)$'
	)
	max_output_length: int = Field(
		default=10000, description='最大输出长度（字符）', gt=0
	)

	# 自定义扩展
	custom_tools: list[Tool] = Field(default_factory=list, description='自定义 Tools')
	tool_filter: Callable[[str, dict[str, Any]], bool] | None = Field(
		default=None, description='Tool 过滤器函数，接收工具名和参数，返回是否允许'
	)

	# 安全配置
	auth_required: bool = Field(default=False, description='是否需要认证')
	allowed_origins: list[str] = Field(
		default_factory=lambda: ['*'], description='允许的 CORS 来源'
	)
	enable_access_logging: bool = Field(
		default=False, description='是否启用访问日志记录'
	)
	mask_sensitive_data: bool = Field(default=True, description='是否脱敏敏感数据')
	path_patterns: list[str] = Field(
		default_factory=list, description='允许的路径模式列表，支持通配符'
	)
	allowed_tags: list[str] = Field(
		default_factory=list, description='允许的标签列表，为空表示允许所有'
	)
	blocked_tags: list[str] = Field(default_factory=list, description='禁止的标签列表')

	# Pydantic 配置
	model_config = ConfigDict(arbitrary_types_allowed=True)
