"""
JsonFormatter 测试
"""

import json
from typing import Any

import pytest

from openapi_mcp.formatters.json import JsonFormatter


@pytest.fixture
def formatter() -> JsonFormatter:
	"""创建 JsonFormatter 实例"""
	return JsonFormatter()


@pytest.fixture
def formatter_with_limit() -> JsonFormatter:
	"""创建有长度限制的 JsonFormatter 实例"""
	return JsonFormatter(max_length=300)


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
			{'name': 'id', 'type': 'integer', 'required': True},
			{'name': 'email', 'type': 'string', 'required': True},
		],
	}


@pytest.fixture
def sample_search_results() -> list[dict[str, str]]:
	"""示例搜索结果"""
	return [
		{'method': 'GET', 'path': '/users', 'summary': 'List all users'},
		{'method': 'GET', 'path': '/users/{id}', 'summary': 'Get user by ID'},
	]


class TestJsonFormatter:
	"""JsonFormatter 测试"""

	def test_format_endpoints(
		self,
		formatter: JsonFormatter,
		sample_endpoints: dict[str, list[dict[str, str]]],
	) -> None:
		"""测试格式化接口列表"""
		result = formatter.format_endpoints(sample_endpoints)

		data = json.loads(result)
		assert 'endpoints' in data
		assert 'total' in data
		assert data['total'] == 3
		assert 'Users' in data['endpoints']
		assert 'Items' in data['endpoints']
		assert len(data['endpoints']['Users']) == 2
		assert len(data['endpoints']['Items']) == 1

	def test_format_endpoints_empty(self, formatter: JsonFormatter) -> None:
		"""测试格式化空接口列表"""
		result = formatter.format_endpoints({})

		data = json.loads(result)
		assert data['total'] == 0
		assert data['endpoints'] == {}

	def test_format_endpoint_details(
		self, formatter: JsonFormatter, sample_endpoint_details: dict[str, Any]
	) -> None:
		"""测试格式化接口详情"""
		result = formatter.format_endpoint_details(sample_endpoint_details)

		data = json.loads(result)
		assert data['method'] == 'POST'
		assert data['path'] == '/users'
		assert data['summary'] == 'Create a new user'
		assert (
			data['description'] == 'Creates a new user with the provided information.'
		)

	def test_format_models(
		self, formatter: JsonFormatter, sample_models: list[dict[str, str]]
	) -> None:
		"""测试格式化模型列表"""
		result = formatter.format_models(sample_models)

		data = json.loads(result)
		assert 'models' in data
		assert 'total' in data
		assert data['total'] == 2
		assert len(data['models']) == 2
		assert data['models'][0]['name'] == 'User'
		assert data['models'][1]['name'] == 'Item'

	def test_format_models_empty(self, formatter: JsonFormatter) -> None:
		"""测试格式化空模型列表"""
		result = formatter.format_models([])

		data = json.loads(result)
		assert data['total'] == 0
		assert data['models'] == []

	def test_format_model_details(
		self, formatter: JsonFormatter, sample_model_details: dict[str, Any]
	) -> None:
		"""测试格式化模型详情"""
		result = formatter.format_model_details(sample_model_details)

		data = json.loads(result)
		assert data['name'] == 'User'
		assert data['description'] == 'User data model'
		assert len(data['fields']) == 2

	def test_format_search_results(
		self, formatter: JsonFormatter, sample_search_results: list[dict[str, str]]
	) -> None:
		"""测试格式化搜索结果"""
		result = formatter.format_search_results(sample_search_results)

		data = json.loads(result)
		assert 'results' in data
		assert 'total' in data
		assert data['total'] == 2
		assert len(data['results']) == 2

	def test_format_search_results_empty(self, formatter: JsonFormatter) -> None:
		"""测试格式化空搜索结果"""
		result = formatter.format_search_results([])

		data = json.loads(result)
		assert data['total'] == 0
		assert data['results'] == []

	def test_truncate_no_limit(self, formatter: JsonFormatter) -> None:
		"""测试无长度限制时不截断"""
		long_text = 'A' * 1000

		result = formatter.truncate(long_text)

		assert len(result) == 1000
		assert result == long_text

	def test_truncate_with_limit(self, formatter_with_limit: JsonFormatter) -> None:
		"""测试有长度限制时截断"""
		long_text = 'A' * 500

		result = formatter_with_limit.truncate(long_text)

		assert len(result) < len(long_text)
		assert '⚠️ 输出已截断' in result

	def test_json_output_valid(
		self,
		formatter: JsonFormatter,
		sample_endpoints: dict[str, list[dict[str, str]]],
	) -> None:
		"""测试 JSON 输出格式正确"""
		result = formatter.format_endpoints(sample_endpoints)

		# 应该能够正常解析
		data = json.loads(result)
		assert isinstance(data, dict)

	def test_chinese_characters(self, formatter: JsonFormatter) -> None:
		"""测试中文字符正确编码"""
		endpoints = {
			'用户': [{'method': 'GET', 'path': '/用户', 'summary': '获取用户列表'}]
		}

		result = formatter.format_endpoints(endpoints)

		# 应该包含中文字符（ensure_ascii=False）
		assert '用户' in result
		assert '获取用户列表' in result
