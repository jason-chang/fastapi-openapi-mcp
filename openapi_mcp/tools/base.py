"""
MCP Tool 基类

所有自定义 Tool 都应继承此基类并实现 execute() 方法。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from mcp.types import CallToolResult

if TYPE_CHECKING:
	from openapi_mcp.server import OpenApiMcpServer  # type: ignore[import-not-found]


class BaseMcpTool(ABC):
	"""MCP Tool 抽象基类

	所有自定义 Tool 都应继承此基类并实现 execute() 方法。
	基类提供了访问 OpenAPI schema 的通用接口。

	Attributes:
		name: Tool 名称，必须是唯一的标识符
		description: Tool 的功能描述，用于 AI 理解工具用途
		input_schema: 输入参数的 JSON Schema 定义，None 表示无参数
	"""

	name: str
	description: str
	input_schema: dict[str, Any] | None = None

	def __init__(self, server: 'OpenApiMcpServer') -> None:
		"""初始化 Tool

		Args:
			server: OpenApiMcpServer 实例，用于访问 OpenAPI schema 和配置
		"""
		self.server = server
		# 获取格式化器
		self._formatter = self._get_formatter()

	def _get_formatter(self):
		"""根据配置获取格式化器

		Returns:
			格式化器实例
		"""
		from openapi_mcp.formatters import (
			JsonFormatter,
			MarkdownFormatter,
			PlainTextFormatter,
		)

		output_format = self.server.config.output_format
		max_length = self.server.config.max_output_length

		if output_format == 'json':
			return JsonFormatter(max_length=max_length)
		elif output_format == 'plain':
			return PlainTextFormatter(max_length=max_length)
		else:  # 默认使用 markdown
			return MarkdownFormatter(max_length=max_length)

	def get_openapi_spec(self) -> dict[str, Any]:
		"""获取 OpenAPI specification

		从 server 获取完整的 OpenAPI schema，可能从缓存中获取。

		Returns:
			完整的 OpenAPI specification 字典

		Raises:
			RuntimeError: 当无法获取 OpenAPI schema 时
		"""
		return self.server._get_openapi_spec()

	@abstractmethod
	async def execute(self, **kwargs: Any) -> CallToolResult:
		"""执行 Tool 的核心逻辑

		子类必须实现此方法来定义工具的具体功能。

		Args:
			**kwargs: 工具的输入参数，应符合 input_schema 定义

		Returns:
			MCP CallToolResult，包含工具执行的结果

		Raises:
			ValueError: 当输入参数不符合要求时
			NotImplementedError: 当子类未实现此方法时
		"""
		raise NotImplementedError('子类必须实现 execute() 方法')
