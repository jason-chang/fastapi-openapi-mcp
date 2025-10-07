"""
测试 GenerateExampleTool
"""

import pytest
from fastapi import FastAPI
from mcp.types import CallToolResult, TextContent

from openapi_mcp.server import OpenApiMcpServer
from openapi_mcp.tools.examples import GenerateExampleTool


@pytest.fixture
def examples_test_app() -> FastAPI:
	"""创建用于示例测试的 FastAPI 应用"""
	app = FastAPI(title='Examples Test API', version='1.0.0')

	@app.get('/users', tags=['users'], summary='列出所有用户')
	async def list_users():
		"""获取系统中所有用户的列表"""
		return {'users': []}

	@app.post('/users', tags=['users'])
	async def create_user(user: dict):
		"""创建新用户"""
		return {'id': 1, 'user': user}

	@app.get('/users/{user_id}', tags=['users'])
	async def get_user(user_id: int, include_profile: bool = False):
		"""获取用户详情"""
		return {'user_id': user_id, 'include_profile': include_profile}

	# 添加带请求体验证的接口
	@app.post('/auth/login', tags=['auth'])
	async def login(credentials: dict):
		"""用户登录"""
		return {'token': 'example_token'}

	return app


def get_text_content(result: CallToolResult) -> str:
	"""从 CallToolResult 中提取文本内容"""
	assert len(result.content) > 0
	content = result.content[0]
	assert isinstance(content, TextContent)
	return content.text


class TestGenerateExampleTool:
	"""测试 GenerateExampleTool 的各种场景"""

	async def test_tool_metadata(self, examples_test_app: FastAPI):
		"""测试 Tool 元数据"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		assert tool.name == 'generate_examples'
		assert isinstance(tool.description, str)
		assert len(tool.description) > 0
		assert tool.input_schema is not None
		assert 'path' in tool.input_schema['properties']
		assert 'method' in tool.input_schema['properties']

	async def test_get_request_example(self, examples_test_app: FastAPI):
		"""测试 GET 请求示例生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/users', method='GET')
		output = get_text_content(result)

		assert not result.isError
		assert '# 📝 GET /users 调用示例' in output
		assert 'GET' in output
		assert '/users' in output
		# 应该包含默认格式
		assert 'JSON' in output or 'cURL' in output or 'Python' in output

	async def test_post_request_example(self, examples_test_app: FastAPI):
		"""测试 POST 请求示例生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/users', method='POST')
		output = get_text_content(result)

		assert not result.isError
		assert '# 📝 POST /users 调用示例' in output
		assert 'POST' in output
		assert '/users' in output

		# POST 请求应该包含请求体示例
		assert '请求体' in output or 'JSON' in output

	async def test_path_parameters_example(self, examples_test_app: FastAPI):
		"""测试路径参数示例生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/users/{user_id}', method='GET')
		output = get_text_content(result)

		assert not result.isError
		assert 'GET' in output
		assert '/users/{user_id}' in output

	async def test_query_parameters_example(self, examples_test_app: FastAPI):
		"""测试查询参数示例生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/users/{user_id}', method='GET')
		output = get_text_content(result)

		assert not result.isError
		# 应该包含路径参数的示例
		assert '/users/{user_id}' in output

	async def test_specific_formats(self, examples_test_app: FastAPI):
		"""测试指定格式生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 测试只生成 JSON 和 cURL 格式
		result = await tool.execute(
			path='/users', method='POST', formats=['json', 'curl']
		)
		output = get_text_content(result)

		assert not result.isError
		assert 'JSON' in output
		assert 'cURL' in output
		# 不应该包含其他格式
		assert 'Python' not in output
		assert 'JavaScript' not in output

	async def test_all_formats(self, examples_test_app: FastAPI):
		"""测试所有格式生成"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 生成所有格式
		result = await tool.execute(
			path='/users',
			method='GET',
			formats=['json', 'curl', 'python', 'javascript', 'http', 'postman'],
		)
		output = get_text_content(result)

		assert not result.isError

		# 检查是否包含各种格式
		assert 'JSON' in output
		assert 'cURL' in output
		assert 'Python' in output
		assert 'JavaScript' in output
		assert 'HTTP' in output
		assert 'Postman' in output

	async def test_example_strategies(self, examples_test_app: FastAPI):
		"""测试不同示例策略"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

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

	async def test_custom_server_url(self, examples_test_app: FastAPI):
		"""测试自定义服务器 URL"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		custom_url = 'https://api.myapp.com/v1'
		result = await tool.execute(path='/users', method='GET', server_url=custom_url)
		output = get_text_content(result)

		assert not result.isError
		assert custom_url in output

	async def test_auth_inclusion(self, examples_test_app: FastAPI):
		"""测试认证信息包含"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 包含认证信息（默认）
		result = await tool.execute(path='/users', method='GET', include_auth=True)
		assert not result.isError

		# 不包含认证信息
		result = await tool.execute(path='/users', method='GET', include_auth=False)
		assert not result.isError

	async def test_nonexistent_endpoint(self, examples_test_app: FastAPI):
		"""测试不存在的端点"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/nonexistent', method='GET')
		output = get_text_content(result)

		assert result.isError
		assert '接口不存在' in output
		assert 'GET /nonexistent' in output

	async def test_invalid_http_method(self, examples_test_app: FastAPI):
		"""测试无效的 HTTP 方法"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(path='/users', method='INVALID')
		output = get_text_content(result)

		assert result.isError
		assert '无效的 HTTP 方法' in output

	async def test_missing_required_params(self, examples_test_app: FastAPI):
		"""测试缺少必需参数"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 缺少 method
		result = await tool.execute(path='/users')
		assert result.isError
		assert 'path 和 method 参数不能为空' in get_text_content(result)

		# 缺少 path
		result = await tool.execute(method='GET')
		assert result.isError
		assert 'path 和 method 参数不能为空' in get_text_content(result)

	async def test_invalid_formats(self, examples_test_app: FastAPI):
		"""测试无效的格式"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(
			path='/users', method='GET', formats=['invalid_format']
		)
		output = get_text_content(result)

		assert result.isError
		assert '无效的格式' in output

	async def test_invalid_example_strategy(self, examples_test_app: FastAPI):
		"""测试无效的示例策略"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		result = await tool.execute(
			path='/users', method='GET', example_strategy='invalid'
		)
		output = get_text_content(result)

		assert result.isError
		assert '无效的示例策略' in output

	async def test_empty_parameters(self, examples_test_app: FastAPI):
		"""测试空参数处理"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 空路径
		result = await tool.execute(path='', method='GET')
		assert result.isError

		# 空方法
		result = await tool.execute(path='/users', method='')
		assert result.isError

	async def test_special_characters_in_path(self, examples_test_app: FastAPI):
		"""测试路径中的特殊字符"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 测试带路径参数的路径
		result = await tool.execute(path='/users/{user_id}', method='GET')
		output = get_text_content(result)

		assert not result.isError
		assert '/users/{user_id}' in output

	async def test_unicode_support(self, examples_test_app: FastAPI):
		"""测试 Unicode 支持"""
		mcp_server = OpenApiMcpServer(examples_test_app)
		tool = GenerateExampleTool(mcp_server)

		# 使用包含中文的自定义服务器 URL
		custom_url = 'https://示例.服务器.com'
		result = await tool.execute(path='/users', method='GET', server_url=custom_url)
		output = get_text_content(result)

		assert not result.isError
		# 检查是否正确处理了 Unicode
		assert len(output) > 0


if __name__ == '__main__':
	pytest.main([__file__])
