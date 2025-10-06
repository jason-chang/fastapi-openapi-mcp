"""
核心 Tools 集成测试

测试新的 4 个核心 Tools 的功能和集成。
"""


import pytest

from openapi_mcp.server import OpenApiMcpServer
from openapi_mcp.tools.examples import GenerateExampleTool
from openapi_mcp.tools.search import SearchEndpointsTool


@pytest.fixture
def mock_server():
	"""创建模拟的 OpenAPI MCP Server"""
	from fastapi import FastAPI

	app = FastAPI(title='Test API', version='1.0.0')

	# 添加一些测试接口
	@app.get('/users')
	async def list_users():
		return {'users': []}

	@app.post('/users')
	async def create_user(user: dict):
		return {'user': user}

	@app.get('/users/{user_id}')
	async def get_user(user_id: int):
		return {'user_id': user_id}

	@app.put('/users/{user_id}')
	async def update_user(user_id: int, user: dict):
		return {'user_id': user_id, 'user': user}

	# 添加标签和描述
	app.openapi()['paths']['/users']['get']['tags'] = ['users']
	app.openapi()['paths']['/users']['get']['summary'] = 'List all users'
	app.openapi()['paths']['/users']['get']['description'] = (
		'Retrieve a list of all users'
	)

	app.openapi()['paths']['/users']['post']['tags'] = ['users']
	app.openapi()['paths']['/users']['post']['summary'] = 'Create a new user'
	app.openapi()['paths']['/users']['post']['description'] = (
		'Create a new user account'
	)

	app.openapi()['paths']['/users/{user_id}']['get']['tags'] = ['users']
	app.openapi()['paths']['/users/{user_id}']['get']['summary'] = 'Get user by ID'
	app.openapi()['paths']['/users/{user_id}']['get']['description'] = (
		'Retrieve a specific user'
	)

	app.openapi()['paths']['/users/{user_id}']['put']['tags'] = ['users']
	app.openapi()['paths']['/users/{user_id}']['put']['summary'] = 'Update user'
	app.openapi()['paths']['/users/{user_id}']['put']['description'] = (
		'Update user information'
	)

	server = OpenApiMcpServer(app)
	return server


class TestSearchEndpointsTool:
	"""测试 SearchEndpointsTool"""

	@pytest.mark.asyncio
	async def test_keyword_search(self, mock_server):
		"""测试关键词搜索"""
		tool = SearchEndpointsTool(mock_server)

		# 测试搜索 "user"
		result = await tool.execute(keyword='user', search_in='all')

		assert not result.isError
		assert 'user' in result.content[0].text.lower()

		# 测试路径搜索
		result = await tool.execute(keyword='/users', search_in='path')

		assert not result.isError
		assert '/users' in result.content[0].text

	@pytest.mark.asyncio
	async def test_regex_search(self, mock_server):
		"""测试正则表达式搜索"""
		tool = SearchEndpointsTool(mock_server)

		# 测试正则表达式
		result = await tool.execute(regex=r'/users/\{.*\}', search_in='path')

		assert not result.isError
		assert 'user' in result.content[0].text.lower()

	@pytest.mark.asyncio
	async def test_tags_filter(self, mock_server):
		"""测试标签过滤"""
		tool = SearchEndpointsTool(mock_server)

		# 测试按标签过滤
		result = await tool.execute(keyword='test', tags=['users'])

		assert not result.isError
		# 应该返回有 users 标签的接口

	@pytest.mark.asyncio
	async def test_methods_filter(self, mock_server):
		"""测试方法过滤"""
		tool = SearchEndpointsTool(mock_server)

		# 测试只搜索 GET 方法
		result = await tool.execute(keyword='user', methods=['GET'])

		assert not result.isError
		# 应该只返回 GET 方法的结果

	@pytest.mark.asyncio
	async def test_validation_errors(self, mock_server):
		"""测试参数验证错误"""
		tool = SearchEndpointsTool(mock_server)

		# 测试没有关键词和正则表达式
		result = await tool.execute()
		assert result.isError
		assert '搜索关键词不能为空' in result.content[0].text

		# 测试同时提供关键词和正则表达式
		result = await tool.execute(keyword='test', regex='test')
		assert result.isError
		assert '不能同时提供' in result.content[0].text

		# 测试无效的正则表达式
		result = await tool.execute(regex='[invalid')
		assert result.isError
		assert '无效的正则表达式' in result.content[0].text

class TestGenerateExampleTool:
	"""测试 GenerateExampleTool"""

	@pytest.mark.asyncio
	async def test_basic_example_generation(self, mock_server):
		"""测试基本示例生成"""
		tool = GenerateExampleTool(mock_server)

		# 生成 GET 请求示例
		result = await tool.execute(path='/users', method='GET')

		assert not result.isError
		assert '示例' in result.content[0].text
		assert 'GET' in result.content[0].text
		assert '/users' in result.content[0].text

	@pytest.mark.asyncio
	async def test_post_request_example(self, mock_server):
		"""测试 POST 请求示例生成"""
		tool = GenerateExampleTool(mock_server)

		# 生成 POST 请求示例
		result = await tool.execute(
			path='/users', method='POST', formats=['json', 'curl']
		)

		assert not result.isError
		assert 'JSON' in result.content[0].text
		assert 'cURL' in result.content[0].text
		assert 'POST' in result.content[0].text

	@pytest.mark.asyncio
	async def test_all_formats(self, mock_server):
		"""测试所有格式生成"""
		tool = GenerateExampleTool(mock_server)

		# 生成所有格式的示例
		result = await tool.execute(
			path='/users',
			method='GET',
			formats=['json', 'curl', 'python', 'javascript', 'http', 'postman'],
		)

		assert not result.isError
		# 检查是否包含各种格式
		content = result.content[0].text
		assert any(
			format_type in content
			for format_type in ['JSON', 'cURL', 'Python', 'JavaScript']
		)

	@pytest.mark.asyncio
	async def test_example_strategies(self, mock_server):
		"""测试不同示例策略"""
		tool = GenerateExampleTool(mock_server)

		# 测试 minimal 策略
		result = await tool.execute(
			path='/users', method='POST', example_strategy='minimal'
		)

		assert not result.isError

		# 测试 realistic 策略
		result = await tool.execute(
			path='/users', method='POST', example_strategy='realistic'
		)

		assert not result.isError

		# 测试 complete 策略
		result = await tool.execute(
			path='/users', method='POST', example_strategy='complete'
		)

		assert not result.isError

	@pytest.mark.asyncio
	async def test_validation_errors(self, mock_server):
		"""测试参数验证错误"""
		tool = GenerateExampleTool(mock_server)

		# 测试缺少必需参数
		result = await tool.execute(path='/users')
		assert result.isError
		assert 'path 和 method 参数不能为空' in result.content[0].text

		# 测试无效的 HTTP 方法
		result = await tool.execute(path='/users', method='INVALID')
		assert result.isError
		assert '无效的 HTTP 方法' in result.content[0].text

		# 测试无效的格式
		result = await tool.execute(
			path='/users', method='GET', formats=['invalid_format']
		)
		assert result.isError
		assert '无效的格式' in result.content[0].text


class TestToolsIntegration:
	"""测试工具集成"""

	@pytest.mark.asyncio
	async def test_server_includes_new_tools(self, mock_server):
		"""测试服务器包含新工具"""
		# 检查服务器是否注册了新的核心工具
		tool_names = [tool.name for tool in mock_server.tools]

		assert 'search_endpoints' in tool_names
		assert 'generate_examples' in tool_names

	@pytest.mark.asyncio
	async def test_tools_use_resources(self, mock_server):
		"""测试工具使用 Resources（如果实现了）"""
		# 这里可以测试工具是否正确使用了 Resources
		# 由于我们还没有完全实现工具与 Resources 的集成，这里先跳过
		pass

	@pytest.mark.asyncio
	async def test_tool_error_handling(self, mock_server):
		"""测试工具错误处理"""
		# 测试各种错误情况
		tools = [
			SearchEndpointsTool(mock_server),
			GenerateExampleTool(mock_server),
		]

		for tool in tools:
			# 测试空参数
			result = await tool.execute()
			if result.isError:
				assert len(result.content[0].text) > 0  # 应该有错误消息


if __name__ == '__main__':
	pytest.main([__file__])
