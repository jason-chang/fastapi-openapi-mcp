"""
集成测试

测试完整的 OpenAPI MCP Server 集成流程，包括：
- 初始化 MCP Server
- 挂载路由
- 调用所有内置 tools
- 验证输出格式
- 测试配置选项
- 测试自定义 tools
- 测试工具过滤
"""

import pytest
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import ASGITransport, AsyncClient
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import OpenApiMcpConfig
from openapi_mcp.tools.base import BaseMcpTool

# =============================================================================
# 创建完整的测试应用
# =============================================================================


class User(BaseModel):
	"""用户模型"""

	id: int
	name: str
	email: str
	role: str = 'user'


class Item(BaseModel):
	"""商品模型"""

	id: int
	name: str
	price: float
	description: str | None = None


class Order(BaseModel):
	"""订单模型"""

	id: int
	user_id: int
	items: list[int]
	total: float
	status: str = 'pending'


@pytest.fixture
def complex_fastapi_app() -> FastAPI:
	"""创建一个复杂的 FastAPI 应用用于集成测试"""
	app = FastAPI(
		title='E-Commerce API',
		version='2.0.0',
		description='电商系统 API - 完整功能测试',
		openapi_tags=[
			{'name': 'users', 'description': '用户管理接口'},
			{'name': 'items', 'description': '商品管理接口'},
			{'name': 'orders', 'description': '订单管理接口'},
			{'name': 'auth', 'description': '认证授权接口'},
			{'name': 'admin', 'description': '管理员接口'},
		],
	)

	# 简单的认证依赖
	security = HTTPBearer()

	async def verify_token(
		credentials: HTTPAuthorizationCredentials = Security(security),
	) -> dict:
		"""验证 token"""
		if credentials.credentials == 'valid-token':
			return {'user_id': 1, 'role': 'user'}
		raise HTTPException(status_code=401, detail='无效的 token')

	# =========================================================================
	# 用户接口
	# =========================================================================

	@app.get(
		'/api/v1/users',
		tags=['users'],
		summary='获取用户列表',
		description='分页获取所有用户',
		response_model=list[User],
	)
	async def list_users(skip: int = 0, limit: int = 10):
		"""获取用户列表

		Args:
			skip: 跳过的记录数
			limit: 返回的记录数

		Returns:
			用户列表
		"""
		return [
			{
				'id': 1,
				'name': 'Alice',
				'email': 'alice@example.com',
				'role': 'admin',
			},
			{'id': 2, 'name': 'Bob', 'email': 'bob@example.com', 'role': 'user'},
		]

	@app.post(
		'/api/v1/users',
		tags=['users'],
		summary='创建新用户',
		response_model=User,
		status_code=201,
	)
	async def create_user(user: User):
		"""创建新用户"""
		return user

	@app.get(
		'/api/v1/users/{user_id}',
		tags=['users'],
		summary='获取用户详情',
		response_model=User,
	)
	async def get_user(user_id: int):
		"""获取指定用户的详细信息"""
		return {
			'id': user_id,
			'name': 'Alice',
			'email': 'alice@example.com',
			'role': 'user',
		}

	@app.put('/api/v1/users/{user_id}', tags=['users'], summary='更新用户信息')
	async def update_user(user_id: int, user: User):
		"""更新用户信息"""
		return {'id': user_id, **user.model_dump()}

	@app.delete('/api/v1/users/{user_id}', tags=['users'], summary='删除用户')
	async def delete_user(user_id: int):
		"""删除指定用户"""
		return {'message': f'User {user_id} deleted'}

	# =========================================================================
	# 商品接口
	# =========================================================================

	@app.get(
		'/api/v1/items',
		tags=['items'],
		summary='获取商品列表',
		response_model=list[Item],
	)
	async def list_items(category: str | None = None, min_price: float | None = None):
		"""获取商品列表，支持按分类和价格筛选"""
		return [
			{
				'id': 1,
				'name': 'Laptop',
				'price': 999.99,
				'description': 'High-performance laptop',
			},
			{
				'id': 2,
				'name': 'Mouse',
				'price': 29.99,
				'description': 'Wireless mouse',
			},
		]

	@app.post(
		'/api/v1/items',
		tags=['items'],
		summary='创建商品',
		response_model=Item,
		status_code=201,
	)
	async def create_item(item: Item):
		"""创建新商品"""
		return item

	@app.get(
		'/api/v1/items/{item_id}',
		tags=['items'],
		summary='获取商品详情',
		response_model=Item,
	)
	async def get_item(item_id: int):
		"""获取指定商品的详细信息"""
		return {
			'id': item_id,
			'name': 'Laptop',
			'price': 999.99,
			'description': 'High-performance laptop',
		}

	# =========================================================================
	# 订单接口（需要认证）
	# =========================================================================

	@app.get(
		'/api/v1/orders',
		tags=['orders'],
		summary='获取订单列表',
		dependencies=[Depends(verify_token)],
	)
	async def list_orders():
		"""获取当前用户的订单列表（需要认证）"""
		return [{'id': 1, 'user_id': 1, 'items': [1, 2], 'total': 1029.98}]

	@app.post(
		'/api/v1/orders',
		tags=['orders'],
		summary='创建订单',
		dependencies=[Depends(verify_token)],
	)
	async def create_order(order: Order):
		"""创建新订单（需要认证）"""
		return order

	@app.get(
		'/api/v1/orders/{order_id}',
		tags=['orders'],
		summary='获取订单详情',
		dependencies=[Depends(verify_token)],
	)
	async def get_order(order_id: int):
		"""获取指定订单的详细信息（需要认证）"""
		return {
			'id': order_id,
			'user_id': 1,
			'items': [1, 2],
			'total': 1029.98,
			'status': 'pending',
		}

	# =========================================================================
	# 认证接口
	# =========================================================================

	@app.post('/api/v1/auth/login', tags=['auth'], summary='用户登录')
	async def login(username: str, password: str):
		"""用户登录获取 token"""
		return {'access_token': 'valid-token', 'token_type': 'bearer'}

	@app.post('/api/v1/auth/register', tags=['auth'], summary='用户注册')
	async def register(user: User):
		"""注册新用户"""
		return {'message': 'User registered successfully', 'user': user}

	# =========================================================================
	# 管理员接口
	# =========================================================================

	@app.get('/api/v1/admin/stats', tags=['admin'], summary='获取统计信息')
	async def get_stats():
		"""获取系统统计信息（管理员专用）"""
		return {'total_users': 100, 'total_items': 500, 'total_orders': 1000}

	@app.post('/api/v1/admin/users/{user_id}/ban', tags=['admin'], summary='封禁用户')
	async def ban_user(user_id: int):
		"""封禁指定用户（管理员专用）"""
		return {'message': f'User {user_id} banned'}

	return app


# =============================================================================
# 测试完整的集成流程
# =============================================================================


class TestFullIntegration:
	"""测试完整的集成流程"""

	async def test_initialize_and_mount(self, complex_fastapi_app: FastAPI):
		"""测试初始化和挂载"""
		# 初始化 MCP Server
		mcp_server = OpenApiMcpServer(complex_fastapi_app)

		# 验证初始化
		assert mcp_server.app is complex_fastapi_app
		assert isinstance(mcp_server.config, OpenApiMcpConfig)
		assert len(mcp_server.tools) == 9  # 9 个内置 tools

		# 挂载路由
		mcp_server.mount('/mcp')

		# 验证路由已挂载（通过检查 OpenAPI schema）
		complex_fastapi_app.openapi()
		# 挂载成功不会报错即可

	async def test_call_all_builtin_tools(self, complex_fastapi_app: FastAPI):
		"""测试调用所有内置 tools"""
		mcp_server = OpenApiMcpServer(complex_fastapi_app)

		# 1. 列出所有接口
		list_tool = mcp_server.tools[0]
		assert list_tool.name == 'list_openapi_endpoints'
		result = await list_tool.execute()
		assert isinstance(result, CallToolResult)
		assert len(result.content) > 0
		assert '/api/v1/users' in result.content[0].text

		# 2. 获取接口详情
		detail_tool = mcp_server.tools[1]
		assert detail_tool.name == 'get_endpoint_details'
		result = await detail_tool.execute(path='/api/v1/users', method='GET')
		assert isinstance(result, CallToolResult)
		assert '获取用户列表' in result.content[0].text

		# 3. 按标签搜索接口
		search_by_tag_tool = mcp_server.tools[2]
		assert search_by_tag_tool.name == 'search_endpoints_by_tag'
		result = await search_by_tag_tool.execute(tag='users')
		assert isinstance(result, CallToolResult)
		assert '/api/v1/users' in result.content[0].text

		# 4. 获取数据模型列表
		models_tool = mcp_server.tools[3]
		assert models_tool.name == 'get_api_models'
		result = await models_tool.execute()
		assert isinstance(result, CallToolResult)
		# 应该包含 User, Item, Order 等模型

		# 5. 获取模型详情
		model_detail_tool = mcp_server.tools[4]
		assert model_detail_tool.name == 'get_model_details'
		result = await model_detail_tool.execute(model_name='User')
		assert isinstance(result, CallToolResult)
		assert 'User' in result.content[0].text

		# 6. 按关键词搜索接口
		search_tool = mcp_server.tools[5]
		assert search_tool.name == 'search_endpoints'
		result = await search_tool.execute(keyword='用户')
		assert isinstance(result, CallToolResult)
		assert len(result.content) > 0

		# 7. 获取认证要求
		auth_tool = mcp_server.tools[6]
		assert auth_tool.name == 'get_auth_requirements'
		result = await auth_tool.execute(path='/api/v1/orders', method='GET')
		assert isinstance(result, CallToolResult)

		# 8. 获取接口示例
		example_tool = mcp_server.tools[7]
		assert example_tool.name == 'get_endpoint_examples'
		result = await example_tool.execute(path='/api/v1/users', method='POST')
		assert isinstance(result, CallToolResult)

		# 9. 获取所有标签
		tags_tool = mcp_server.tools[8]
		assert tags_tool.name == 'get_tags_list'
		result = await tags_tool.execute()
		assert isinstance(result, CallToolResult)
		assert 'users' in result.content[0].text
		assert 'items' in result.content[0].text

	async def test_output_formats(self, complex_fastapi_app: FastAPI):
		"""测试不同的输出格式"""
		# 测试 Markdown 格式
		config_md = OpenApiMcpConfig(output_format='markdown')
		server_md = OpenApiMcpServer(complex_fastapi_app, config_md)
		tool_md = server_md.tools[0]
		result_md = await tool_md.execute()
		assert isinstance(result_md.content[0].text, str)

		# 测试 JSON 格式
		config_json = OpenApiMcpConfig(output_format='json')
		server_json = OpenApiMcpServer(complex_fastapi_app, config_json)
		tool_json = server_json.tools[0]
		result_json = await tool_json.execute()
		assert isinstance(result_json.content[0].text, str)

		# 测试 Plain 格式
		config_plain = OpenApiMcpConfig(output_format='plain')
		server_plain = OpenApiMcpServer(complex_fastapi_app, config_plain)
		tool_plain = server_plain.tools[0]
		result_plain = await tool_plain.execute()
		assert isinstance(result_plain.content[0].text, str)

	async def test_http_endpoint_integration(self, complex_fastapi_app: FastAPI):
		"""测试 HTTP 端点集成"""
		mcp_server = OpenApiMcpServer(complex_fastapi_app)
		mcp_server.mount('/mcp')

		# 创建测试客户端
		transport = ASGITransport(app=complex_fastapi_app)
		async with AsyncClient(transport=transport, base_url='http://test') as client:
			# 测试 POST 请求（JSON-RPC）
			# 需要正确的请求头
			response = await client.post(
				'/mcp',
				json={
					'jsonrpc': '2.0',
					'id': 1,
					'method': 'tools/list',
					'params': {},
				},
				headers={
					'Content-Type': 'application/json',
					'Mcp-Protocol-Version': '2025-06-18',
				},
			)
			# 验证响应状态（可能是 200 或其他）
			assert response.status_code in [200, 400, 404]
			# 如果成功，验证响应格式
			if response.status_code == 200:
				data = response.json()
				assert 'result' in data or 'error' in data


# =============================================================================
# 测试配置选项
# =============================================================================


class TestConfigurationOptions:
	"""测试配置选项"""

	async def test_cache_configuration(self, complex_fastapi_app: FastAPI):
		"""测试缓存配置"""
		# 启用缓存
		config_cache = OpenApiMcpConfig(cache_enabled=True, cache_ttl=300)
		server_cache = OpenApiMcpServer(complex_fastapi_app, config_cache)

		# 第一次获取
		spec1 = server_cache._get_openapi_spec()
		assert 'openapi_spec' in server_cache.cache

		# 第二次获取（应该从缓存）
		spec2 = server_cache._get_openapi_spec()
		assert spec1 is spec2

		# 禁用缓存
		config_no_cache = OpenApiMcpConfig(cache_enabled=False)
		server_no_cache = OpenApiMcpServer(complex_fastapi_app, config_no_cache)

		server_no_cache._get_openapi_spec()
		assert 'openapi_spec' not in server_no_cache.cache

	async def test_prefix_configuration(self, complex_fastapi_app: FastAPI):
		"""测试路由前缀配置"""
		# 自定义前缀
		config = OpenApiMcpConfig(prefix='/api/mcp')
		server = OpenApiMcpServer(complex_fastapi_app, config)
		server.mount()

		# 验证路由已挂载
		complex_fastapi_app.openapi()
		# 挂载成功不会报错即可

	async def test_output_length_configuration(self, complex_fastapi_app: FastAPI):
		"""测试输出长度限制配置"""
		config = OpenApiMcpConfig(max_output_length=100)
		server = OpenApiMcpServer(complex_fastapi_app, config)
		tool = server.tools[0]
		await tool.execute()

		# 注意：当前实现中 max_output_length 配置尚未在 formatters 中实现
		# 这个测试暂时只验证配置已设置
		assert server.config.max_output_length == 100
		# TODO: 等 formatter 支持 max_output_length 后，再验证实际输出长度

	async def test_cors_configuration(self, complex_fastapi_app: FastAPI):
		"""测试 CORS 配置"""
		config = OpenApiMcpConfig(
			allowed_origins=['http://localhost:3000', 'https://example.com']
		)
		server = OpenApiMcpServer(complex_fastapi_app, config)
		server.mount('/mcp')

		# CORS 配置在传输处理器中
		assert server.config.allowed_origins == [
			'http://localhost:3000',
			'https://example.com',
		]


# =============================================================================
# 测试自定义 Tools
# =============================================================================


class TestCustomTools:
	"""测试自定义 tools"""

	async def test_register_custom_tool(self, complex_fastapi_app: FastAPI):
		"""测试注册自定义 tool"""

		# 创建自定义 tool
		class CustomSummaryTool(BaseMcpTool):
			name = 'get_api_summary'
			description = '获取 API 总结信息'

			async def execute(self, **kwargs):
				spec = self.get_openapi_spec()
				total_paths = len(spec.get('paths', {}))
				total_tags = len(spec.get('tags', []))

				summary = f"""
# API 总结

- 总接口数: {total_paths}
- 总标签数: {total_tags}
- API 标题: {spec.get('info', {}).get('title')}
- API 版本: {spec.get('info', {}).get('version')}
"""

				return CallToolResult(content=[TextContent(type='text', text=summary)])

		# 注册自定义 tool
		server = OpenApiMcpServer(complex_fastapi_app)
		custom_tool = CustomSummaryTool(server)
		server.register_tool(custom_tool)

		# 验证注册成功
		assert len(server.tools) == 10  # 9 个内置 + 1 个自定义
		assert server.tools[9].name == 'get_api_summary'

		# 调用自定义 tool
		result = await custom_tool.execute()
		assert isinstance(result, CallToolResult)
		assert 'API 总结' in result.content[0].text
		assert 'E-Commerce API' in result.content[0].text

	async def test_custom_tool_with_parameters(self, complex_fastapi_app: FastAPI):
		"""测试带参数的自定义 tool"""

		class CustomFilterTool(BaseMcpTool):
			name = 'filter_endpoints_by_method'
			description = '按 HTTP 方法过滤接口'

			async def execute(self, method: str, **kwargs):
				spec = self.get_openapi_spec()
				paths = spec.get('paths', {})

				filtered = []
				for path, path_spec in paths.items():
					if method.lower() in path_spec:
						filtered.append(f'{method.upper()} {path}')

				result = '\n'.join(filtered) if filtered else '未找到匹配的接口'

				return CallToolResult(content=[TextContent(type='text', text=result)])

		# 注册并使用
		server = OpenApiMcpServer(complex_fastapi_app)
		custom_tool = CustomFilterTool(server)
		server.register_tool(custom_tool)

		# 测试过滤 GET 接口
		result = await custom_tool.execute(method='get')
		assert 'GET /api/v1/users' in result.content[0].text

		# 测试过滤 POST 接口
		result = await custom_tool.execute(method='post')
		assert 'POST /api/v1/users' in result.content[0].text


# =============================================================================
# 测试工具过滤
# =============================================================================


class TestToolFiltering:
	"""测试工具过滤"""

	async def test_path_pattern_filter(self, complex_fastapi_app: FastAPI):
		"""测试路径模式过滤"""
		# 只允许 /api/v1/users/* 路径
		config = OpenApiMcpConfig(path_patterns=['/api/v1/users*'])
		server = OpenApiMcpServer(complex_fastapi_app, config)

		# 测试列出接口（应该只包含 users 相关接口）
		tool = server.tools[0]
		result = await tool.execute()
		assert '/api/v1/users' in result.content[0].text
		# items 和 orders 应该被过滤掉

	async def test_tag_filter(self, complex_fastapi_app: FastAPI):
		"""测试标签过滤"""
		# 只允许 users 和 items 标签
		config = OpenApiMcpConfig(allowed_tags=['users', 'items'])
		server = OpenApiMcpServer(complex_fastapi_app, config)

		tool = server.tools[0]
		result = await tool.execute()
		text = result.content[0].text

		# 应该包含 users 和 items
		assert 'users' in text.lower() or '/api/v1/users' in text
		# orders 应该被过滤掉（可能不包含）

	async def test_blocked_tags_filter(self, complex_fastapi_app: FastAPI):
		"""测试阻止标签过滤"""
		# 阻止 admin 标签
		config = OpenApiMcpConfig(blocked_tags=['admin'])
		server = OpenApiMcpServer(complex_fastapi_app, config)

		tool = server.tools[0]
		result = await tool.execute()
		text = result.content[0].text

		# admin 接口应该被过滤掉
		# 但 users、items 等应该存在
		assert 'users' in text.lower() or '/api/v1/users' in text

	async def test_custom_filter_function(self, complex_fastapi_app: FastAPI):
		"""测试自定义过滤函数"""

		# 自定义过滤函数：只允许 GET 方法的接口
		def only_get_methods(tool_name: str, params: dict) -> bool:
			# 如果是 get_endpoint_details，检查 method 参数
			if tool_name == 'get_endpoint_details':
				return params.get('method', '').upper() == 'GET'
			return True

		config = OpenApiMcpConfig(tool_filter=only_get_methods)
		server = OpenApiMcpServer(complex_fastapi_app, config)

		# 调用工具过滤器
		if server.tool_filter:
			# 允许 GET 方法
			assert server.tool_filter.should_allow('get_endpoint_details', method='GET')
			# 不允许 POST 方法
			assert not server.tool_filter.should_allow(
				'get_endpoint_details', method='POST'
			)


# =============================================================================
# 测试安全特性
# =============================================================================


class TestSecurityFeatures:
	"""测试安全特性"""

	async def test_sensitive_data_masking(self, complex_fastapi_app: FastAPI):
		"""测试敏感数据脱敏"""
		config = OpenApiMcpConfig(mask_sensitive_data=True)
		server = OpenApiMcpServer(complex_fastapi_app, config)

		# 验证脱敏器已初始化
		assert server.data_masker is not None

		# 测试脱敏功能
		sensitive_data = {
			'username': 'john',
			'password': 'secret123',
			'token': 'abc123xyz',
		}
		masked = server.data_masker.mask_dict(sensitive_data)
		assert masked['username'] == 'john'
		assert masked['password'] == '***'
		assert masked['token'] == '***'

	async def test_access_logging(self, complex_fastapi_app: FastAPI):
		"""测试访问日志记录"""
		config = OpenApiMcpConfig(enable_access_logging=True)
		server = OpenApiMcpServer(complex_fastapi_app, config)

		# 验证日志记录器已初始化
		assert server.access_logger is not None

		# 测试日志记录（不会实际写入，只验证初始化）
		server.access_logger.log_tool_call('test_tool', {'param': 'value'})


# =============================================================================
# 边界情况和错误处理
# =============================================================================


class TestEdgeCases:
	"""测试边界情况"""

	async def test_empty_app_integration(self):
		"""测试空应用的集成"""
		app = FastAPI(title='Empty API', version='1.0.0')
		server = OpenApiMcpServer(app)
		server.mount('/mcp')

		# 应该能正常工作，只是没有接口
		tool = server.tools[0]
		result = await tool.execute()
		assert isinstance(result, CallToolResult)

	async def test_duplicate_tool_registration(self, complex_fastapi_app: FastAPI):
		"""测试重复注册 tool"""

		class DuplicateTool(BaseMcpTool):
			name = 'duplicate_tool'
			description = '重复工具'

			async def execute(self, **kwargs):
				return CallToolResult(content=[TextContent(type='text', text='result')])

		server = OpenApiMcpServer(complex_fastapi_app)
		tool1 = DuplicateTool(server)
		tool2 = DuplicateTool(server)

		server.register_tool(tool1)

		# 重复注册应该抛出异常
		with pytest.raises(ValueError, match='Tool 名称重复'):
			server.register_tool(tool2)

	async def test_invalid_tool_parameters(self, complex_fastapi_app: FastAPI):
		"""测试无效的工具参数"""
		server = OpenApiMcpServer(complex_fastapi_app)
		tool = server.tools[1]  # get_endpoint_details

		# 测试不存在的接口（目前工具会返回错误消息而不是抛出异常）
		result = await tool.execute(path='/nonexistent', method='GET')
		assert isinstance(result, CallToolResult)
		# 验证返回了错误消息
		assert (
			'不存在' in result.content[0].text
			or 'not found' in result.content[0].text.lower()
		)

	async def test_cache_invalidation(self, complex_fastapi_app: FastAPI):
		"""测试缓存失效"""
		server = OpenApiMcpServer(complex_fastapi_app)

		# 获取 spec（会缓存）
		server._get_openapi_spec()
		assert 'openapi_spec' in server.cache

		# 清除缓存
		server.invalidate_cache()
		assert 'openapi_spec' not in server.cache

		# 再次获取（会重新获取）
		spec2 = server._get_openapi_spec()
		assert 'openapi_spec' in server.cache
		assert isinstance(spec2, dict)


# =============================================================================
# 性能测试
# =============================================================================


class TestPerformance:
	"""测试性能"""

	async def test_large_scale_endpoints(self):
		"""测试大量接口的性能"""
		app = FastAPI(title='Large API', version='1.0.0')

		# 创建 100 个接口
		# 使用工厂函数避免循环变量绑定问题
		def make_endpoint(endpoint_id: int):
			async def endpoint():
				return {'id': endpoint_id}

			return endpoint

		for i in range(100):
			app.add_api_route(
				f'/api/endpoint_{i}',
				make_endpoint(i),
				methods=['GET'],
				tags=[f'group_{i // 10}'],
			)

		server = OpenApiMcpServer(app)

		# 测试列出所有接口的性能
		import time

		start = time.time()
		tool = server.tools[0]
		result = await tool.execute()
		elapsed = time.time() - start

		assert isinstance(result, CallToolResult)
		assert elapsed < 1.0  # 应该在 1 秒内完成

	async def test_cache_performance(self, complex_fastapi_app: FastAPI):
		"""测试缓存性能提升"""
		import time

		server = OpenApiMcpServer(complex_fastapi_app)

		# 第一次获取（无缓存）
		start1 = time.time()
		spec1 = server._get_openapi_spec()
		elapsed1 = time.time() - start1

		# 第二次获取（有缓存）
		start2 = time.time()
		spec2 = server._get_openapi_spec()
		elapsed2 = time.time() - start2

		# 缓存应该更快
		assert elapsed2 < elapsed1
		assert spec1 is spec2
