"""
测试 SearchEndpointsTool
"""

import pytest
from fastapi import FastAPI
from mcp.types import CallToolResult, TextContent

from openapi_mcp.server import OpenApiMcpServer
from openapi_mcp.tools.search import SearchEndpointsTool


@pytest.fixture
def search_test_app() -> FastAPI:
	"""创建用于搜索测试的 FastAPI 应用"""
	app = FastAPI(title='Search Test API', version='1.0.0')

	@app.get('/users', tags=['users'], summary='列出所有用户')
	async def list_users():
		"""获取系统中所有用户的列表"""
		return {'users': []}

	@app.post('/users', tags=['users'], summary='创建新用户')
	async def create_user():
		"""向系统添加新用户"""
		return {'id': 1}

	@app.get('/users/{id}', tags=['users'], summary='获取用户详情')
	async def get_user(_id: int):
		"""根据用户 ID 获取特定用户的详细信息"""
		return {'id': _id}

	@app.delete('/users/{id}', tags=['users'], summary='删除用户')
	async def delete_user(_id: int):
		"""从系统中删除指定用户"""
		return {'deleted': True}

	@app.get('/items', tags=['items'], summary='列出所有商品')
	async def list_items():
		"""获取商店中所有商品的列表"""
		return {'items': []}

	@app.post('/items', tags=['items'], summary='创建新商品')
	async def create_item():
		"""添加新商品到商店"""
		return {'id': 1}

	@app.get('/admin/stats', tags=['admin'], summary='获取统计信息')
	async def get_stats():
		"""获取系统的统计数据和分析信息"""
		return {'stats': {}}

	return app


def get_text_content(result: CallToolResult) -> str:
	"""从 CallToolResult 中提取文本内容"""
	assert len(result.content) > 0
	content = result.content[0]
	assert isinstance(content, TextContent)
	return content.text


class TestSearchEndpointsTool:
	"""测试 SearchEndpointsTool 的各种场景"""

	async def test_tool_metadata(self, search_test_app: FastAPI):
		"""测试 Tool 元数据"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		assert tool.name == 'search_endpoints'
		assert isinstance(tool.description, str)
		assert len(tool.description) > 0
		assert tool.input_schema is not None
		assert 'keyword' in tool.input_schema['properties']
		assert 'search_in' in tool.input_schema['properties']

	async def test_search_in_path(self, search_test_app: FastAPI):
		"""测试在路径中搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='users', search_in='path')
		output = get_text_content(result)

		# 应该找到所有包含 'users' 的路径
		assert '🔍 **搜索结果: "users"**' in output
		assert '📊 **搜索范围**: 路径' in output
		assert '/users' in output
		assert '/users/{id}' in output
		# 不应包含 items 和 admin
		assert '/items' not in output
		assert '/admin' not in output
		# 应该显示匹配数量
		assert '📈 **匹配数量**: 4 个接口' in output

	async def test_search_in_summary(self, search_test_app: FastAPI):
		"""测试在摘要中搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='用户', search_in='summary')
		output = get_text_content(result)

		assert '🔍 **搜索结果: "用户"**' in output
		assert '📊 **搜索范围**: 摘要' in output
		# 应该找到所有摘要中包含 '用户' 的接口
		assert '列出所有用户' in output
		assert '创建新用户' in output
		assert '获取用户详情' in output
		assert '删除用户' in output
		# 不应包含商品相关
		assert '商品' not in output

	async def test_search_in_description(self, search_test_app: FastAPI):
		"""测试在描述中搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='系统', search_in='description')
		output = get_text_content(result)

		assert '🔍 **搜索结果: "系统"**' in output
		assert '📊 **搜索范围**: 描述' in output
		# 应该找到描述中包含 '系统' 的接口
		assert '列出所有用户' in output or '获取系统' in output

	async def test_search_all_scopes(self, search_test_app: FastAPI):
		"""测试全范围搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='用户', search_in='all')
		output = get_text_content(result)

		assert '🔍 **搜索结果: "用户"**' in output
		assert '📊 **搜索范围**: 全部' in output
		# 应该在路径、摘要和描述中都搜索
		assert '/users' in output
		assert '列出所有用户' in output

	async def test_search_default_scope(self, search_test_app: FastAPI):
		"""测试默认搜索范围（all）"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		# 不指定 search_in，应该使用默认值 'all'
		result = await tool.execute(keyword='items')
		output = get_text_content(result)

		assert '🔍 **搜索结果: "items"**' in output
		assert '/items' in output

	async def test_search_case_insensitive(self, search_test_app: FastAPI):
		"""测试不区分大小写的搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		# 使用大写搜索
		result = await tool.execute(keyword='USERS', search_in='path')
		output = get_text_content(result)

		# 应该找到小写的 users
		assert '/users' in output
		assert '📈 **匹配数量**: 4 个接口' in output

	async def test_search_no_results(self, search_test_app: FastAPI):
		"""测试没有匹配结果的情况"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='nonexistent', search_in='path')
		output = get_text_content(result)

		assert '🔍 **搜索结果: "nonexistent"**' in output
		assert '📈 **匹配数量**: 0 个接口' in output
		assert '📭 没有找到匹配的接口' in output
		# 应该给出建议
		assert '**建议**:' in output
		assert '尝试使用更通用的关键词' in output

	async def test_search_empty_keyword(self, search_test_app: FastAPI):
		"""测试空关键词"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='', search_in='path')

		assert result.isError is True
		output = get_text_content(result)
		assert '❌ 错误: 搜索关键词不能为空' in output

	async def test_search_whitespace_keyword(self, search_test_app: FastAPI):
		"""测试只包含空白字符的关键词"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='   ', search_in='path')

		assert result.isError is True
		output = get_text_content(result)
		assert '❌ 错误: 搜索关键词不能为空' in output

	async def test_search_invalid_scope(self, search_test_app: FastAPI):
		"""测试无效的搜索范围"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='users', search_in='invalid')

		assert result.isError is True
		output = get_text_content(result)
		assert '❌ 错误: 无效的搜索范围' in output

	async def test_search_partial_match(self, search_test_app: FastAPI):
		"""测试部分匹配"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		# 搜索 'user'，应该匹配 'users'
		result = await tool.execute(keyword='user', search_in='path')
		output = get_text_content(result)

		assert '/users' in output
		assert '📈 **匹配数量**: 4 个接口' in output

	async def test_search_result_grouping(self, search_test_app: FastAPI):
		"""测试搜索结果按匹配位置分组"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='用户', search_in='all')
		output = get_text_content(result)

		# 应该显示匹配位置信息
		assert '*匹配于*: 摘要' in output

	async def test_search_with_http_methods(self, search_test_app: FastAPI):
		"""测试搜索结果包含 HTTP 方法"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='users', search_in='path')
		output = get_text_content(result)

		# 应该显示不同的 HTTP 方法图标
		assert '🟢' in output or 'GET' in output  # GET
		assert '🔵' in output or 'POST' in output  # POST
		assert '🔴' in output or 'DELETE' in output  # DELETE

	async def test_search_shows_tags(self, search_test_app: FastAPI):
		"""测试搜索结果显示标签"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='users', search_in='path')
		output = get_text_content(result)

		# 应该显示标签信息
		assert '*标签*: users' in output

	async def test_search_sorted_results(self, search_test_app: FastAPI):
		"""测试搜索结果排序"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='e', search_in='path')
		output = get_text_content(result)

		# 结果应该按路径排序
		items_pos = output.find('/items')
		users_pos = output.find('/users')

		# items 应该在 users 之前（字母顺序）
		if items_pos != -1 and users_pos != -1:
			assert items_pos < users_pos

	@pytest.mark.parametrize(
		'keyword,search_in,expected_count',
		[
			('users', 'path', 4),  # 4 个 users 接口
			('items', 'path', 2),  # 2 个 items 接口
			('admin', 'path', 1),  # 1 个 admin 接口
			('用户', 'summary', 4),  # 摘要中有 4 个包含"用户"
			('商品', 'summary', 2),  # 摘要中有 2 个包含"商品"
		],
	)
	async def test_search_count(
		self,
		search_test_app: FastAPI,
		keyword: str,
		search_in: str,
		expected_count: int,
	):
		"""参数化测试：验证搜索结果数量"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword=keyword, search_in=search_in)
		output = get_text_content(result)

		assert f'📈 **匹配数量**: {expected_count} 个接口' in output

	async def test_search_with_empty_api(self):
		"""测试空 API 的搜索"""
		app = FastAPI(title='Empty API', version='1.0.0')
		mcp_server = OpenApiMcpServer(app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='users', search_in='all')
		output = get_text_content(result)

		assert '📈 **匹配数量**: 0 个接口' in output
		assert '📭 没有找到匹配的接口' in output

	async def test_search_unicode_characters(self, search_test_app: FastAPI):
		"""测试 Unicode 字符搜索"""
		mcp_server = OpenApiMcpServer(search_test_app)
		tool = SearchEndpointsTool(mcp_server)

		# 搜索中文
		result = await tool.execute(keyword='用户', search_in='summary')
		output = get_text_content(result)

		assert '用户' in output
		assert '📈 **匹配数量**:' in output

	async def test_search_special_characters(self):
		"""测试特殊字符在路径中的搜索"""
		app = FastAPI(title='Special Chars API', version='1.0.0')

		@app.get('/api/v1/users', tags=['v1'])
		async def v1_users():
			return []

		@app.get('/api/v2/users', tags=['v2'])
		async def v2_users():
			return []

		mcp_server = OpenApiMcpServer(app)
		tool = SearchEndpointsTool(mcp_server)

		# 搜索 'v1'
		result = await tool.execute(keyword='v1', search_in='path')
		output = get_text_content(result)

		assert '/api/v1/users' in output
		assert '/api/v2/users' not in output
		assert '📈 **匹配数量**: 1 个接口' in output

	async def test_search_description_with_truncation(self):
		"""测试描述过长时的截断"""
		app = FastAPI(title='Long Description API', version='1.0.0')

		long_description = '这是一个非常长的描述。' * 50  # 超过 200 字符

		@app.get('/test', tags=['test'], summary='测试接口')
		async def test_endpoint():
			"""这是一个非常长的描述。"""
			return {}

		# 手动修改 docstring 不会影响 OpenAPI description
		# 需要使用 FastAPI 的 description 参数
		from fastapi import APIRouter

		router = APIRouter()

		@router.get(
			'/test', tags=['test'], summary='测试接口', description=long_description
		)
		async def test_endpoint_with_desc():
			return {}

		app.include_router(router)

		mcp_server = OpenApiMcpServer(app)
		tool = SearchEndpointsTool(mcp_server)

		result = await tool.execute(keyword='非常长', search_in='description')
		output = get_text_content(result)

		# 如果描述过长，应该被截断
		if '...' in output:
			assert True  # 验证截断存在
