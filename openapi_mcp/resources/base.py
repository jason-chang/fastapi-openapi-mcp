"""
Resource 基础类

定义所有 MCP Resources 的基础接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar
from urllib.parse import unquote

from mcp.types import Resource, TextContent
from pydantic import AnyUrl


class BaseResource(ABC):
	"""MCP Resource 基础类

	所有 Resource 实现的抽象基类，定义了通用的接口和功能。

	Attributes:
	    uri_template: URI 模板，用于匹配请求的 URI
	    name: Resource 名称
	    description: Resource 描述
	    mime_type: Resource MIME 类型，默认为 'application/json'
	"""

	uri_template: ClassVar[str]
	name: ClassVar[str]
	description: ClassVar[str]
	mime_type: ClassVar[str] = 'application/json'

	def __init__(self, server) -> None:
		"""初始化 Resource

		Args:
		    server: OpenApiMcpServer 实例，用于获取 OpenAPI spec
		"""
		self.server = server

	@abstractmethod
	async def read(self, uri: str) -> str:
		"""读取 Resource 内容

		Args:
		    uri: 请求的 URI

		Returns:
		    Resource 内容字符串

		Raises:
		    ValueError: 当 URI 不匹配时
		    RuntimeError: 当无法获取数据时
		"""
		...

	def matches_uri(self, uri: str) -> bool:
		"""检查 URI 是否匹配此 Resource

		Args:
		    uri: 请求的 URI

		Returns:
		    True 如果 URI 匹配此 Resource
		"""
		# 特殊处理端点路径参数，路径可能包含斜杠
		if self.uri_template == 'openapi://endpoints/{path}':
			# 匹配 openapi://endpoints/{path} 格式
			if uri.startswith('openapi://endpoints/'):
				return True
			return False

		# 简单的模板匹配，支持路径参数
		template_parts = self.uri_template.split('/')
		uri_parts = uri.split('/')

		if len(template_parts) != len(uri_parts):
			return False

		for template_part, uri_part in zip(template_parts, uri_parts, strict=False):
			# 路径参数以 { } 包围
			if template_part.startswith('{') and template_part.endswith('}'):
				continue
			# 精确匹配
			if template_part != uri_part:
				return False

		return True

	def extract_params(self, uri: str) -> dict[str, str]:
		"""从 URI 中提取路径参数

		Args:
		    uri: 请求的 URI

		Returns:
		    路径参数字典

		Raises:
		    ValueError: 当 URI 不匹配时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		# 特殊处理端点路径参数
		if self.uri_template == 'openapi://endpoints/{path}':
			# 提取 openapi://endpoints/ 后面的路径
			path = uri[len('openapi://endpoints/') :]
			# URL 解码
			path = unquote(path)
			# 如果路径为空，则默认为根路径
			if not path:
				path = '/'
			return {'path': path}

		template_parts = self.uri_template.split('/')
		uri_parts = uri.split('/')

		params: dict[str, str] = {}
		for template_part, uri_part in zip(template_parts, uri_parts, strict=False):
			if template_part.startswith('{') and template_part.endswith('}'):
				param_name = template_part[1:-1]
				# URL 解码
				params[param_name] = unquote(uri_part)

		return params

	def to_resource_info(self) -> Resource:
		"""转换为 MCP Resource 信息

		Returns:
		    符合 MCP 规范的 Resource 对象
		"""
		return Resource(
			uri=AnyUrl(self.uri_template),
			name=self.name,
			description=self.description,
			mimeType=self.mime_type,
		)

	async def get_openapi_spec(self) -> dict[str, Any]:
		"""获取 OpenAPI spec

		通过 server 实例获取缓存的 OpenAPI spec。

		Returns:
		    OpenAPI specification 字典

		Raises:
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		return self.server._get_openapi_spec()

	def create_text_content(self, text: str) -> TextContent:
		"""创建文本内容

		Args:
		    text: 文本内容

		Returns:
		    TextContent 对象
		"""
		return TextContent(type='text', text=text)
