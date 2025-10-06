"""
测试 BaseMcpTool 基类
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.types import CallToolResult, TextContent

from openapi_mcp.tools.base import BaseMcpTool


class ConcreteTool(BaseMcpTool):
	"""测试用的具体 Tool 实现"""

	name = 'test_tool'
	description = '测试工具'
	input_schema = {
		'type': 'object',
		'properties': {'param': {'type': 'string', 'description': '测试参数'}},
		'required': ['param'],
	}

	async def execute(self, **kwargs: Any) -> CallToolResult:
		"""实现 execute 方法"""
		param = kwargs.get('param', 'default')
		return CallToolResult(
			content=[TextContent(type='text', text=f'执行结果: {param}')]
		)


class AbstractTool(BaseMcpTool):
	"""未实现 execute 方法的 Tool（用于测试抽象方法强制实现）"""

	name = 'abstract_tool'
	description = '抽象工具'


@pytest.fixture
def mock_server() -> MagicMock:
	"""创建 mock 的 OpenApiMcpServer"""
	server = MagicMock()
	server._get_openapi_spec.return_value = {
		'openapi': '3.0.0',
		'info': {'title': 'Test API', 'version': '1.0.0'},
		'paths': {
			'/users': {
				'get': {'summary': 'List users', 'tags': ['users']},
			}
		},
	}
	return server


class TestBaseMcpTool:
	"""测试 BaseMcpTool 基类"""

	def test_tool_initialization(self, mock_server: MagicMock) -> None:
		"""测试 Tool 初始化"""
		tool = ConcreteTool(mock_server)

		assert tool.server is mock_server
		assert tool.name == 'test_tool'
		assert tool.description == '测试工具'
		assert tool.input_schema is not None
		assert tool.input_schema['type'] == 'object'

	def test_get_openapi_spec(self, mock_server: MagicMock) -> None:
		"""测试获取 OpenAPI spec"""
		tool = ConcreteTool(mock_server)

		spec = tool.get_openapi_spec()

		assert spec is not None
		assert spec['openapi'] == '3.0.0'
		assert 'paths' in spec
		assert '/users' in spec['paths']
		mock_server._get_openapi_spec.assert_called_once()

	async def test_execute_implementation(self, mock_server: MagicMock) -> None:
		"""测试 execute 方法的实现"""
		tool = ConcreteTool(mock_server)

		result = await tool.execute(param='test_value')

		assert isinstance(result, CallToolResult)
		assert len(result.content) == 1
		text_content = result.content[0]
		assert isinstance(text_content, TextContent)
		assert text_content.type == 'text'
		assert '执行结果: test_value' in text_content.text

	async def test_execute_with_default_value(self, mock_server: MagicMock) -> None:
		"""测试 execute 方法使用默认值"""
		tool = ConcreteTool(mock_server)

		result = await tool.execute()

		assert isinstance(result, CallToolResult)
		text_content = result.content[0]
		assert isinstance(text_content, TextContent)
		assert '执行结果: default' in text_content.text

	def test_abstract_method_enforcement(self, mock_server: MagicMock) -> None:
		"""测试抽象方法必须实现"""
		# Python 的 ABC 在实例化时就会检查抽象方法
		# 尝试创建未实现 execute 方法的实例应该抛出 TypeError
		with pytest.raises(
			TypeError,
			match="Can't instantiate abstract class AbstractTool without an implementation for abstract method 'execute'",
		):
			AbstractTool(mock_server)  # type: ignore[abstract]

	def test_tool_without_input_schema(self, mock_server: MagicMock) -> None:
		"""测试没有输入参数的 Tool"""

		class NoInputTool(BaseMcpTool):
			name = 'no_input_tool'
			description = '无输入参数的工具'
			input_schema = None

			async def execute(self, **kwargs: Any) -> CallToolResult:
				return CallToolResult(
					content=[TextContent(type='text', text='无参数执行')]
				)

		tool = NoInputTool(mock_server)

		assert tool.input_schema is None
		assert tool.name == 'no_input_tool'

	async def test_tool_execution_without_schema(self, mock_server: MagicMock) -> None:
		"""测试无 schema 的 Tool 可以正常执行"""

		class NoInputTool(BaseMcpTool):
			name = 'no_input_tool'
			description = '无输入参数的工具'
			input_schema = None

			async def execute(self, **kwargs: Any) -> CallToolResult:
				return CallToolResult(
					content=[TextContent(type='text', text='无参数执行')]
				)

		tool = NoInputTool(mock_server)
		result = await tool.execute()

		assert isinstance(result, CallToolResult)
		text_content = result.content[0]
		assert isinstance(text_content, TextContent)
		assert '无参数执行' in text_content.text

	def test_get_openapi_spec_multiple_calls(self, mock_server: MagicMock) -> None:
		"""测试多次调用 get_openapi_spec"""
		tool = ConcreteTool(mock_server)

		spec1 = tool.get_openapi_spec()
		spec2 = tool.get_openapi_spec()

		assert spec1 == spec2
		# 验证调用了两次（没有在 Tool 层面缓存）
		assert mock_server._get_openapi_spec.call_count == 2

	def test_tool_attributes_are_class_level(self, mock_server: MagicMock) -> None:
		"""测试 Tool 属性是类级别的"""
		tool1 = ConcreteTool(mock_server)
		tool2 = ConcreteTool(mock_server)

		# name 和 description 应该是相同的（类属性）
		assert tool1.name == tool2.name
		assert tool1.description == tool2.description
		assert tool1.input_schema == tool2.input_schema

	async def test_execute_with_multiple_params(self, mock_server: MagicMock) -> None:
		"""测试带多个参数的 execute 方法"""

		class MultiParamTool(BaseMcpTool):
			name = 'multi_param_tool'
			description = '多参数工具'
			input_schema = {
				'type': 'object',
				'properties': {
					'param1': {'type': 'string'},
					'param2': {'type': 'integer'},
				},
			}

			async def execute(self, **kwargs: Any) -> CallToolResult:
				param1 = kwargs.get('param1', 'default1')
				param2 = kwargs.get('param2', 0)
				return CallToolResult(
					content=[
						TextContent(
							type='text', text=f'参数1: {param1}, 参数2: {param2}'
						)
					]
				)

		tool = MultiParamTool(mock_server)
		result = await tool.execute(param1='test', param2=42)

		text_content = result.content[0]
		assert isinstance(text_content, TextContent)
		assert '参数1: test, 参数2: 42' in text_content.text
