"""
格式化器集成测试
"""

import pytest
from fastapi import FastAPI

from openapi_mcp import OpenApiMcpConfig, OpenApiMcpServer
from openapi_mcp.formatters import JsonFormatter, MarkdownFormatter, PlainTextFormatter


@pytest.fixture
def test_app():
	"""创建测试用的 FastAPI 应用"""
	app = FastAPI(title='Test API', version='1.0.0', description='测试API')

	@app.get('/users')
	async def list_users():
		"""列出用户"""
		return {'users': []}

	@app.post('/users')
	async def create_user(user_data: dict):
		"""创建用户"""
		return {'user': user_data}

	@app.get('/users/{user_id}')
	async def get_user(user_id: int):
		"""获取用户详情"""
		return {'user_id': user_id, 'name': 'Test User'}

	return app


@pytest.mark.asyncio
async def test_markdown_formatter(test_app):
	"""测试 Markdown 格式化器"""
	config = OpenApiMcpConfig(output_format='markdown')
	server = OpenApiMcpServer(test_app, config)

	# 测试 SearchEndpointsTool
	list_tool = server.tools[0]
	result = await list_tool.execute()

	assert not result.isError
	assert result.content[0].type == 'text'

	text = result.content[0].text
	assert '🚀 **Available API Endpoints:**' in text
	assert '`/users`' in text
	assert '**GET**' in text
	assert '📊 **Total endpoints:** 3' in text


@pytest.mark.asyncio
async def test_json_formatter(test_app):
	"""测试 JSON 格式化器"""
	config = OpenApiMcpConfig(output_format='json')
	server = OpenApiMcpServer(test_app, config)

	# 测试 SearchEndpointsTool
	list_tool = server.tools[0]
	result = await list_tool.execute()

	assert not result.isError
	assert result.content[0].type == 'text'

	text = result.content[0].text
	# 验证是有效的 JSON
	import json

	data = json.loads(text)

	assert 'endpoints' in data
	assert 'total' in data
	assert data['total'] == 3
	assert 'default' in data['endpoints']
	assert len(data['endpoints']['default']) == 3


@pytest.mark.asyncio
async def test_plain_formatter(test_app):
	"""测试纯文本格式化器"""
	config = OpenApiMcpConfig(output_format='plain')
	server = OpenApiMcpServer(test_app, config)

	# 测试 SearchEndpointsTool
	list_tool = server.tools[0]
	result = await list_tool.execute()

	assert not result.isError
	assert result.content[0].type == 'text'

	text = result.content[0].text
	assert 'Available API Endpoints:' in text
	assert 'GET /users' in text
	assert 'Total endpoints: 3' in text
	# 确保没有 Markdown 语法
	assert '**' not in text
	assert '`' not in text


@pytest.mark.asyncio
async def test_formatter_length_limit(test_app):
	"""测试格式化器长度限制"""
	config = OpenApiMcpConfig(
		output_format='markdown',
		max_output_length=100,  # 很小的限制
	)
	server = OpenApiMcpServer(test_app, config)

	list_tool = server.tools[0]
	result = await list_tool.execute()

	assert not result.isError
	text = result.content[0].text
	# 应该包含截断信息
	assert '⚠️ 输出已截断' in text or 'truncated' in text.lower()


def test_formatter_selection():
	"""测试格式化器选择逻辑"""
	# 测试默认选择
	config1 = OpenApiMcpConfig()
	assert config1.output_format == 'markdown'

	# 测试有效格式
	for format_type in ['markdown', 'json', 'plain']:
		config2 = OpenApiMcpConfig(output_format=format_type)
		assert config2.output_format == format_type

	# 测试无效格式会被 Pydantic 验证拒绝
	import pytest

	with pytest.raises(Exception):  # Pydantic ValidationError
		OpenApiMcpConfig(output_format='invalid')


def test_formatter_classes():
	"""测试格式化器类实例化"""
	# 测试各种格式化器可以正常实例化
	formatter1 = MarkdownFormatter(max_length=1000)
	assert formatter1.max_length == 1000

	formatter2 = JsonFormatter(max_length=2000)
	assert formatter2.max_length == 2000

	formatter3 = PlainTextFormatter(max_length=500)
	assert formatter3.max_length == 500
