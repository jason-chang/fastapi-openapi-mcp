"""
OpenAPI MCP Server 核心类

提供将 FastAPI 应用的 OpenAPI 文档转换为 MCP Tools 的核心功能。
"""

from typing import Any

from fastapi import FastAPI

from openapi_mcp.cache import OpenApiCache
from openapi_mcp.config import OpenApiMcpConfig
from openapi_mcp.resources.manager import ResourceManager
from openapi_mcp.security import AccessLogger, SensitiveDataMasker, ToolFilter
from openapi_mcp.tools.base import BaseMcpTool


class OpenApiMcpServer:
	"""OpenAPI MCP Server

	将 FastAPI 应用的 OpenAPI 文档转换为 MCP Tools，
	让 AI 编程助手能够高效查询 API 信息。

	主要功能：
	- 自动获取 FastAPI 的 OpenAPI schema
	- 缓存 OpenAPI schema 以提升性能
	- 注册和管理内置的 MCP Tools
	- 支持自定义配置和扩展

	Example:
		>>> from fastapi import FastAPI
		>>> from openapi_mcp import OpenApiMcpServer, OpenApiMcpConfig
		>>>
		>>> app = FastAPI(title='My API', version='1.0.0')
		>>>
		>>> @app.get('/users')
		>>> async def list_users():
		...     return {'users': []}
		>>>
		>>> config = OpenApiMcpConfig(cache_ttl=600)
		>>> mcp_server = OpenApiMcpServer(app, config)
		>>> mcp_server.mount('/mcp')

	Attributes:
		app: FastAPI 应用实例
		config: MCP Server 配置
		cache: OpenAPI schema 缓存管理器
		tools: 已注册的 MCP Tools 列表
		resources: Resource 管理器，用于管理 MCP Resources
		tool_filter: 工具过滤器（可选）
		data_masker: 敏感信息脱敏器（可选）
		access_logger: 访问日志记录器（可选）
	"""

	def __init__(self, app: FastAPI, config: OpenApiMcpConfig | None = None) -> None:
		"""初始化 OpenAPI MCP Server

		Args:
			app: FastAPI 应用实例
			config: 可选的配置对象，未提供则使用默认配置

		Raises:
			TypeError: 当 app 不是 FastAPI 实例时
		"""
		if not isinstance(app, FastAPI):
			raise TypeError(f'app 必须是 FastAPI 实例，收到: {type(app).__name__}')

		self.app = app
		self.config = config or OpenApiMcpConfig()
		self.cache = OpenApiCache()
		self.tools: list[BaseMcpTool] = []
		self.resources = ResourceManager()

		# 初始化安全组件
		self.tool_filter: ToolFilter | None = None
		self.data_masker: SensitiveDataMasker | None = None
		self.access_logger: AccessLogger | None = None

		# 如果配置了过滤规则，初始化工具过滤器
		if (
			self.config.path_patterns
			or self.config.allowed_tags
			or self.config.blocked_tags
			or self.config.tool_filter
		):
			self.tool_filter = ToolFilter(
				path_patterns=self.config.path_patterns,
				allowed_tags=self.config.allowed_tags,
				blocked_tags=self.config.blocked_tags,
				custom_filter=self.config.tool_filter,
			)

		# 如果启用敏感数据脱敏，初始化脱敏器
		if self.config.mask_sensitive_data:
			self.data_masker = SensitiveDataMasker()

		# 如果启用访问日志，初始化日志记录器
		if self.config.enable_access_logging:
			self.access_logger = AccessLogger(
				mask_sensitive=self.config.mask_sensitive_data,
				masker=self.data_masker,
			)

		# 注册内置 Tools 和 Resources
		self._register_builtin_tools()
		self._register_builtin_resources()

	def _get_openapi_spec(self) -> dict[str, Any]:
		"""获取 OpenAPI specification

		如果启用缓存且缓存存在，则从缓存返回；
		否则从 FastAPI app 获取并缓存。

		Returns:
			完整的 OpenAPI specification 字典

		Raises:
			RuntimeError: 当无法获取 OpenAPI schema 时
		"""
		cache_key = 'openapi_spec'

		# 如果启用缓存，尝试从缓存获取
		if self.config.cache_enabled:
			cached_spec = self.cache.get(cache_key)
			if cached_spec is not None:
				return cached_spec

		# 从 FastAPI 获取 OpenAPI schema
		try:
			spec = self.app.openapi()
		except Exception as e:
			raise RuntimeError(f'无法获取 OpenAPI schema: {e}') from e

		if not isinstance(spec, dict):
			raise RuntimeError(
				f'OpenAPI schema 必须是字典类型，收到: {type(spec).__name__}'
			)

		# 存入缓存
		if self.config.cache_enabled:
			self.cache.set(cache_key, spec, ttl=self.config.cache_ttl)

		return spec

	def _register_builtin_tools(self) -> None:
		"""注册内置的 MCP Tools

		此方法会在初始化时调用，注册所有内置的 Tools。

		Tools:
		- SearchEndpointsTool: 高级搜索接口，支持关键词、正则表达式、标签、方法过滤
		- GenerateExampleTool: 生成各种格式的调用示例 (JSON, cURL, Python, JavaScript等)
		"""
		# 导入工具
		from openapi_mcp.tools.examples import GenerateExampleTool
		from openapi_mcp.tools.search import SearchEndpointsTool
		# 注册 Tools
		self.tools.append(SearchEndpointsTool(self))  # 增强的搜索工具
		self.tools.append(GenerateExampleTool(self))  # 新增的示例生成工具

	def _register_builtin_resources(self) -> None:
		"""注册内置的 MCP Resources

		此方法会在初始化时调用，注册所有内置的 Resources。

		已实现的 Resources:
		- OpenApiSpecResource: 完整的 OpenAPI spec
		- EndpointsListResource: 端点列表
		- EndpointResource: 具体端点详情
		- ModelsListResource: 数据模型列表
		- ModelResource: 具体模型详情
		- TagsListResource: 标签列表
		- TagEndpointsResource: 按标签分组的端点
		"""
		# 延迟导入避免循环依赖
		from openapi_mcp.resources.endpoints import (
			EndpointResource,
			EndpointsListResource,
		)
		from openapi_mcp.resources.models import ModelResource, ModelsListResource
		from openapi_mcp.resources.spec import OpenApiSpecResource
		from openapi_mcp.resources.tags import TagEndpointsResource, TagsListResource

		# 注册内置 Resources
		self.resources.register_resource(OpenApiSpecResource(self))
		self.resources.register_resource(EndpointsListResource(self))
		self.resources.register_resource(EndpointResource(self))
		self.resources.register_resource(ModelsListResource(self))
		self.resources.register_resource(ModelResource(self))
		self.resources.register_resource(TagsListResource(self))
		self.resources.register_resource(TagEndpointsResource(self))

	def register_tool(self, tool: BaseMcpTool) -> None:
		"""注册自定义 MCP Tool

		允许用户注册自定义的 Tool 扩展功能。

		Args:
			tool: BaseMcpTool 的实例

		Raises:
			TypeError: 当 tool 不是 BaseMcpTool 的实例时
			ValueError: 当 tool 的 name 与已存在的 tool 重复时
		"""
		if not isinstance(tool, BaseMcpTool):
			raise TypeError(
				f'tool 必须是 BaseMcpTool 的实例，收到: {type(tool).__name__}'
			)

		# 检查是否有重名的 tool
		for existing_tool in self.tools:
			if existing_tool.name == tool.name:
				raise ValueError(f'Tool 名称重复: {tool.name}')

		self.tools.append(tool)

	def get_resource_manager(self) -> ResourceManager:
		"""获取 Resource 管理器

		Returns:
			ResourceManager 实例
		"""
		return self.resources

	def mount(self, prefix: str | None = None) -> None:
		"""将 MCP Server 挂载到 FastAPI 应用

		在 FastAPI 应用上挂载 MCP 相关的路由端点，符合 MCP 2025-06-18 标准。
		挂载单个端点同时支持 POST、GET、DELETE 方法。

		Args:
			prefix: 路由前缀，None 则使用配置中的默认值

		Example:
			>>> mcp_server = OpenApiMcpServer(app)
			>>> mcp_server.mount('/mcp')  # 挂载到 /mcp 端点
		"""
		from fastapi import Header, Request

		from openapi_mcp.transport import McpTransportHandler

		# 使用配置中的 prefix 或传入的 prefix
		actual_prefix = prefix if prefix is not None else self.config.prefix

		# 创建传输处理器
		transport_handler = McpTransportHandler(
			tools=self.tools,
			resources=self.resources,
			allowed_origins=self.config.allowed_origins,
			tool_filter=self.tool_filter,
			data_masker=self.data_masker,
			access_logger=self.access_logger,
		)

		# 挂载单个 MCP 端点
		@self.app.post(actual_prefix)
		@self.app.get(actual_prefix)
		@self.app.delete(actual_prefix)
		async def mcp_endpoint(
			request: Request,
			mcp_protocol_version: str | None = Header(
				None, alias='Mcp-Protocol-Version'
			),
			mcp_session_id: str | None = Header(None, alias='Mcp-Session-Id'),
			origin: str | None = Header(None),
			accept: str | None = Header(None),
			last_event_id: str | None = Header(None, alias='Last-Event-Id'),
		):
			"""MCP 统一端点

			根据 HTTP 方法路由到不同的处理器：
			- POST: 处理 JSON-RPC 请求
			- GET: 打开 SSE 流
			- DELETE: 终止会话
			"""
			if request.method == 'POST':
				return await transport_handler.handle_post(
					request=request,
					mcp_protocol_version=mcp_protocol_version,
					mcp_session_id=mcp_session_id,
					origin=origin,
					accept=accept,
				)
			elif request.method == 'GET':
				return await transport_handler.handle_get(
					mcp_protocol_version=mcp_protocol_version,
					mcp_session_id=mcp_session_id,
					origin=origin,
					accept=accept,
					last_event_id=last_event_id,
				)
			elif request.method == 'DELETE':
				return await transport_handler.handle_delete(
					mcp_protocol_version=mcp_protocol_version,
					mcp_session_id=mcp_session_id,
					origin=origin,
				)

	def invalidate_cache(self) -> None:
		"""清除 OpenAPI schema 缓存

		当 FastAPI 应用的路由发生变化时，调用此方法清除缓存，
		确保下次获取的是最新的 OpenAPI schema。

		Example:
			>>> mcp_server = OpenApiMcpServer(app)
			>>> # 动态添加新路由后
			>>> mcp_server.invalidate_cache()
		"""
		self.cache.invalidate('openapi_spec')

	def get_registered_tools(self) -> list[BaseMcpTool]:
		"""获取所有已注册的 Tools

		Returns:
			已注册的 Tool 列表
		"""
		return self.tools.copy()
