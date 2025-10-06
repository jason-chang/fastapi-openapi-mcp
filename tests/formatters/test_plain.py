"""
PlainTextFormatter 测试
"""

from typing import Any

import pytest

from openapi_mcp.formatters.plain import PlainTextFormatter


@pytest.fixture
def formatter() -> PlainTextFormatter:
	"""创建 PlainTextFormatter 实例"""
	return PlainTextFormatter()


@pytest.fixture
def formatter_with_limit() -> PlainTextFormatter:
	"""创建有长度限制的 PlainTextFormatter 实例"""
	return PlainTextFormatter(max_length=500)


@pytest.fixture
def sample_endpoints() -> dict[str, list[dict[str, str]]]:
	"""示例接口列表"""
	return {
		'Users': [
			{'method': 'GET', 'path': '/users', 'summary': 'List all users'},
			{'method': 'POST', 'path': '/users', 'summary': 'Create a new user'},
		],
		'Items': [
			{'method': 'GET', 'path': '/items', 'summary': 'List all items'},
		],
	}


@pytest.fixture
def sample_endpoint_details() -> dict[str, Any]:
	"""示例接口详情"""
	return {
		'method': 'POST',
		'path': '/users',
		'summary': 'Create a new user',
		'description': 'Creates a new user with the provided information.',
		'parameters': [
			{
				'name': 'api_key',
				'in': 'header',
				'required': True,
				'type': 'string',
				'description': 'API authentication key',
			}
		],
		'requestBody': {
			'required': True,
			'content': {
				'application/json': {
					'schema': {'$ref': '#/components/schemas/UserCreate'}
				}
			},
		},
		'responses': {
			'201': {
				'description': 'User created successfully',
				'content': {
					'application/json': {
						'schema': {'$ref': '#/components/schemas/User'}
					}
				},
			},
			'400': {'description': 'Invalid request'},
		},
		'security': [{'BearerAuth': ['write:users']}],
	}


@pytest.fixture
def sample_models() -> list[dict[str, str]]:
	"""示例模型列表"""
	return [
		{'name': 'User', 'description': 'User data model'},
		{'name': 'Item', 'description': 'Item data model'},
	]


@pytest.fixture
def sample_model_details() -> dict[str, Any]:
	"""示例模型详情"""
	return {
		'name': 'User',
		'description': 'User data model',
		'fields': [
			{
				'name': 'id',
				'type': 'integer',
				'required': True,
				'description': 'User ID',
			},
			{
				'name': 'email',
				'type': 'string',
				'required': True,
				'description': 'User email',
				'format': 'email',
				'maxLength': 100,
			},
			{
				'name': 'name',
				'type': 'string',
				'required': False,
				'description': 'User name',
				'minLength': 1,
				'maxLength': 50,
			},
		],
		'required': ['id', 'email'],
	}


@pytest.fixture
def sample_search_results() -> list[dict[str, str]]:
	"""示例搜索结果"""
	return [
		{'method': 'GET', 'path': '/users', 'summary': 'List all users'},
		{'method': 'GET', 'path': '/users/{id}', 'summary': 'Get user by ID'},
	]


class TestPlainTextFormatter:
	"""PlainTextFormatter 测试"""

	def test_format_endpoints(
		self,
		formatter: PlainTextFormatter,
		sample_endpoints: dict[str, list[dict[str, str]]],
	) -> None:
		"""测试格式化接口列表"""
		result = formatter.format_endpoints(sample_endpoints)

		assert 'Available API Endpoints:' in result
		assert '[Users]' in result
		assert '[Items]' in result
		assert 'GET /users - List all users' in result
		assert 'POST /users - Create a new user' in result
		assert 'GET /items - List all items' in result
		assert 'Total endpoints: 3' in result

	def test_format_endpoints_empty(self, formatter: PlainTextFormatter) -> None:
		"""测试格式化空接口列表"""
		result = formatter.format_endpoints({})

		assert 'No endpoints found.' in result

	def test_format_endpoints_untagged(self, formatter: PlainTextFormatter) -> None:
		"""测试格式化无标签接口"""
		endpoints = {
			'Untagged': [
				{'method': 'GET', 'path': '/health', 'summary': 'Health check'}
			]
		}

		result = formatter.format_endpoints(endpoints)

		assert '[Untagged]' in result
		assert 'GET /health - Health check' in result

	def test_format_endpoint_details(
		self, formatter: PlainTextFormatter, sample_endpoint_details: dict[str, Any]
	) -> None:
		"""测试格式化接口详情"""
		result = formatter.format_endpoint_details(sample_endpoint_details)

		assert 'POST /users' in result
		assert 'Create a new user' in result
		assert 'Creates a new user with the provided information.' in result
		assert 'Parameters:' in result
		assert 'api_key (header) [Required]: string' in result
		assert 'Request Body:' in result
		assert 'Content-Type: application/json' in result
		assert 'Schema: UserCreate' in result
		assert 'Responses:' in result
		assert '201 - User created successfully' in result
		assert '400 - Invalid request' in result
		assert 'Security:' in result
		assert '- BearerAuth' in result
		assert 'write:users' in result

	def test_format_endpoint_details_deprecated(
		self, formatter: PlainTextFormatter
	) -> None:
		"""测试格式化废弃的接口"""
		endpoint_info = {
			'method': 'GET',
			'path': '/old-endpoint',
			'summary': 'Old endpoint',
			'deprecated': True,
		}

		result = formatter.format_endpoint_details(endpoint_info)

		assert 'WARNING: This endpoint is deprecated.' in result

	def test_format_models(
		self, formatter: PlainTextFormatter, sample_models: list[dict[str, str]]
	) -> None:
		"""测试格式化模型列表"""
		result = formatter.format_models(sample_models)

		assert 'API Data Models (2 models):' in result
		assert '- User: User data model' in result
		assert '- Item: Item data model' in result
		assert 'Use get_model_details to view full schema.' in result

	def test_format_models_empty(self, formatter: PlainTextFormatter) -> None:
		"""测试格式化空模型列表"""
		result = formatter.format_models([])

		assert 'No models found.' in result

	def test_format_model_details(
		self, formatter: PlainTextFormatter, sample_model_details: dict[str, Any]
	) -> None:
		"""测试格式化模型详情"""
		result = formatter.format_model_details(sample_model_details)

		assert 'Model: User' in result
		assert 'Description: User data model' in result
		assert 'Fields:' in result
		assert '- id [Required]: integer' in result
		assert '- email [Required]: string' in result
		assert 'format: email' in result
		assert 'maxLength: 100' in result
		assert '- name: string' in result
		assert 'minLength: 1' in result
		assert 'maxLength: 50' in result
		assert 'Required fields: id, email' in result

	def test_format_search_results(
		self, formatter: PlainTextFormatter, sample_search_results: list[dict[str, str]]
	) -> None:
		"""测试格式化搜索结果"""
		result = formatter.format_search_results(sample_search_results)

		assert 'Search Results (2 endpoints):' in result
		assert 'GET /users - List all users' in result
		assert 'GET /users/{id} - Get user by ID' in result

	def test_format_search_results_empty(self, formatter: PlainTextFormatter) -> None:
		"""测试格式化空搜索结果"""
		result = formatter.format_search_results([])

		assert 'No results found.' in result

	def test_truncate_no_limit(self, formatter: PlainTextFormatter) -> None:
		"""测试无长度限制时不截断"""
		long_text = 'A' * 10000

		result = formatter.truncate(long_text)

		assert len(result) == 10000
		assert result == long_text

	def test_truncate_with_limit(
		self, formatter_with_limit: PlainTextFormatter
	) -> None:
		"""测试有长度限制时截断"""
		long_text = 'A' * 1000

		result = formatter_with_limit.truncate(long_text)

		assert len(result) < len(long_text)
		assert '⚠️ 输出已截断' in result
		assert '总长度: 1000 字符' in result
		assert '限制: 500 字符' in result
