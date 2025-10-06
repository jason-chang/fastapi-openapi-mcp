"""
测试 OpenApiMcpServer 核心类
"""

import pytest
from fastapi import FastAPI

from openapi_mcp.config import OpenApiMcpConfig
from openapi_mcp.server import OpenApiMcpServer
from openapi_mcp.tools.base import BaseMcpTool


@pytest.fixture
def simple_app() -> FastAPI:
	"""创建简单的 FastAPI 应用用于测试"""
	app = FastAPI(title='Test API', version='1.0.0', description='测试 API')

	@app.get('/users', tags=['users'])
	async def list_users():
		"""列出所有用户"""
		return {'users': []}

	@app.post('/users', tags=['users'])
	async def create_user():
		"""创建新用户"""
		return {'id': 1}

	@app.get('/items/{item_id}', tags=['items'])
	async def get_item(item_id: int):
		"""获取指定商品"""
		return {'id': item_id}

	return app


@pytest.fixture
def complex_app() -> FastAPI:
	"""创建更复杂的 FastAPI 应用用于测试"""
	app = FastAPI(
		title='Complex API',
		version='2.0.0',
		description='复杂的测试 API',
		openapi_tags=[
			{'name': 'users', 'description': '用户管理'},
			{'name': 'items', 'description': '商品管理'},
			{'name': 'auth', 'description': '认证授权'},
		],
	)

	@app.get('/api/v1/users', tags=['users'])
	async def list_users(skip: int = 0, limit: int = 10):
		"""列出所有用户"""
		return {'users': [], 'skip': skip, 'limit': limit}

	@app.post('/api/v1/users', tags=['users'])
	async def create_user():
		"""创建新用户"""
		return {'id': 1}

	@app.get('/api/v1/users/{user_id}', tags=['users'])
	async def get_user(user_id: int):
		"""获取指定用户"""
		return {'id': user_id}

	@app.get('/api/v1/items', tags=['items'])
	async def list_items():
		"""列出所有商品"""
		return {'items': []}

	@app.post('/api/v1/auth/login', tags=['auth'])
	async def login():
		"""用户登录"""
		return {'token': 'abc123'}

	return app


class TestOpenApiMcpServerInit:
	"""测试 OpenApiMcpServer 初始化"""

	def test_init_with_default_config(self, simple_app: FastAPI):
		"""测试使用默认配置初始化"""
		server = OpenApiMcpServer(simple_app)

		assert server.app is simple_app
		assert isinstance(server.config, OpenApiMcpConfig)
		assert server.config.cache_enabled is True
		assert server.config.cache_ttl == 300
		assert isinstance(server.tools, list)
		assert len(server.tools) == 9  # 有 9 个内置 tools

	def test_init_with_custom_config(self, simple_app: FastAPI):
		"""测试使用自定义配置初始化"""
		config = OpenApiMcpConfig(
			cache_enabled=False,
			cache_ttl=600,
			prefix='/api/mcp',
			output_format='json',
		)
		server = OpenApiMcpServer(simple_app, config)

		assert server.app is simple_app
		assert server.config is config
		assert server.config.cache_enabled is False
		assert server.config.cache_ttl == 600
		assert server.config.prefix == '/api/mcp'
		assert server.config.output_format == 'json'

	def test_init_with_invalid_app(self):
		"""测试传入非 FastAPI 实例时抛出异常"""
		with pytest.raises(TypeError, match='app 必须是 FastAPI 实例'):
			OpenApiMcpServer('not a FastAPI app')  # type: ignore

		with pytest.raises(TypeError, match='app 必须是 FastAPI 实例'):
			OpenApiMcpServer(None)  # type: ignore


class TestGetOpenApiSpec:
	"""测试获取 OpenAPI specification"""

	def test_get_openapi_spec_simple(self, simple_app: FastAPI):
		"""测试获取简单 API 的 OpenAPI spec"""
		server = OpenApiMcpServer(simple_app)
		spec = server._get_openapi_spec()

		assert isinstance(spec, dict)
		assert spec['openapi'] == '3.1.0'
		assert spec['info']['title'] == 'Test API'
		assert spec['info']['version'] == '1.0.0'
		assert 'paths' in spec
		assert '/users' in spec['paths']
		assert '/items/{item_id}' in spec['paths']

	def test_get_openapi_spec_complex(self, complex_app: FastAPI):
		"""测试获取复杂 API 的 OpenAPI spec"""
		server = OpenApiMcpServer(complex_app)
		spec = server._get_openapi_spec()

		assert isinstance(spec, dict)
		assert spec['info']['title'] == 'Complex API'
		assert spec['info']['version'] == '2.0.0'
		assert '/api/v1/users' in spec['paths']
		assert '/api/v1/items' in spec['paths']
		assert '/api/v1/auth/login' in spec['paths']

	def test_get_openapi_spec_with_cache(self, simple_app: FastAPI):
		"""测试启用缓存时的行为"""
		config = OpenApiMcpConfig(cache_enabled=True, cache_ttl=300)
		server = OpenApiMcpServer(simple_app, config)

		# 第一次获取（应该从 FastAPI 获取）
		spec1 = server._get_openapi_spec()
		assert isinstance(spec1, dict)

		# 第二次获取（应该从缓存获取）
		spec2 = server._get_openapi_spec()
		assert spec1 is spec2  # 应该是同一个对象

		# 验证缓存中确实存在
		assert 'openapi_spec' in server.cache

	def test_get_openapi_spec_without_cache(self, simple_app: FastAPI):
		"""测试禁用缓存时的行为"""
		config = OpenApiMcpConfig(cache_enabled=False)
		server = OpenApiMcpServer(simple_app, config)

		# 第一次获取
		spec1 = server._get_openapi_spec()
		assert isinstance(spec1, dict)

		# 第二次获取（不应该从缓存获取）
		spec2 = server._get_openapi_spec()
		assert isinstance(spec2, dict)

		# 验证缓存为空
		assert 'openapi_spec' not in server.cache


class TestCacheManagement:
	"""测试缓存管理功能"""

	def test_invalidate_cache(self, simple_app: FastAPI):
		"""测试清除缓存"""
		server = OpenApiMcpServer(simple_app)

		# 获取 spec（会缓存）
		server._get_openapi_spec()
		assert 'openapi_spec' in server.cache

		# 清除缓存
		server.invalidate_cache()
		assert 'openapi_spec' not in server.cache

		# 再次获取（会重新从 FastAPI 获取）
		spec2 = server._get_openapi_spec()
		assert isinstance(spec2, dict)
		assert 'openapi_spec' in server.cache

	def test_cache_ttl_expiration(self, simple_app: FastAPI):
		"""测试缓存 TTL 过期"""
		import time

		config = OpenApiMcpConfig(cache_enabled=True, cache_ttl=1)  # 1 秒过期
		server = OpenApiMcpServer(simple_app, config)

		# 获取 spec（会缓存）
		server._get_openapi_spec()
		assert 'openapi_spec' in server.cache

		# 等待缓存过期
		time.sleep(1.1)

		# 缓存应该已过期
		assert 'openapi_spec' not in server.cache

		# 再次获取（会重新从 FastAPI 获取）
		spec2 = server._get_openapi_spec()
		assert isinstance(spec2, dict)


class TestToolsManagement:
	"""测试 Tools 管理功能"""

	def test_register_builtin_tools(self, simple_app: FastAPI):
		"""测试内置 tools 注册"""
		server = OpenApiMcpServer(simple_app)
		assert len(server.tools) == 9  # 应该有 9 个内置 tools
		assert server.tools[0].name == 'list_openapi_endpoints'

	def test_get_registered_tools(self, simple_app: FastAPI):
		"""测试获取已注册的 tools"""
		server = OpenApiMcpServer(simple_app)
		tools = server.get_registered_tools()

		assert isinstance(tools, list)
		assert len(tools) == 9  # 应该有 9 个内置 tools

		# 确保返回的是副本，不是原始列表
		tools.append('fake_tool')  # type: ignore
		assert len(server.tools) == 9

	def test_register_custom_tool(self, simple_app: FastAPI):
		"""测试注册自定义 tool"""
		from mcp.types import CallToolResult, TextContent

		class DummyTool(BaseMcpTool):
			name = 'dummy_tool'
			description = '测试工具'

			async def execute(self, **kwargs):
				return CallToolResult(
					content=[TextContent(type='text', text='dummy result')]
				)

		server = OpenApiMcpServer(simple_app)
		tool = DummyTool(server)

		# 注册 tool
		server.register_tool(tool)

		assert len(server.tools) == 10  # 9 个内置 + 1 个自定义
		assert server.tools[9] is tool  # 自定义 tool 是最后一个
		assert tool.name == 'dummy_tool'

	def test_register_invalid_tool(self, simple_app: FastAPI):
		"""测试注册无效的 tool"""
		server = OpenApiMcpServer(simple_app)

		# 注册非 BaseMcpTool 实例
		with pytest.raises(TypeError, match='tool 必须是 BaseMcpTool 的实例'):
			server.register_tool('not a tool')  # type: ignore

		with pytest.raises(TypeError, match='tool 必须是 BaseMcpTool 的实例'):
			server.register_tool(None)  # type: ignore

	def test_register_duplicate_tool_name(self, simple_app: FastAPI):
		"""测试注册重名的 tool"""
		from mcp.types import CallToolResult, TextContent

		class DummyTool1(BaseMcpTool):
			name = 'duplicate_tool'
			description = '工具1'

			async def execute(self, **kwargs):
				return CallToolResult(
					content=[TextContent(type='text', text='result1')]
				)

		class DummyTool2(BaseMcpTool):
			name = 'duplicate_tool'  # 重名
			description = '工具2'

			async def execute(self, **kwargs):
				return CallToolResult(
					content=[TextContent(type='text', text='result2')]
				)

		server = OpenApiMcpServer(simple_app)
		tool1 = DummyTool1(server)
		tool2 = DummyTool2(server)

		# 注册第一个 tool
		server.register_tool(tool1)
		assert len(server.tools) == 10  # 9 个内置 + 1 个自定义

		# 注册重名 tool 应该失败
		with pytest.raises(ValueError, match='Tool 名称重复: duplicate_tool'):
			server.register_tool(tool2)

		assert (
			len(server.tools) == 10
		)  # 应该保持 9 个内置 + 1 个自定义（失败的注册不应添加）


class TestMount:
	"""测试路由挂载功能"""

	def test_mount_with_default_prefix(self, simple_app: FastAPI):
		"""测试使用默认前缀挂载"""
		server = OpenApiMcpServer(simple_app)

		# 当前为空实现，应该不抛出异常
		server.mount()

	def test_mount_with_custom_prefix(self, simple_app: FastAPI):
		"""测试使用自定义前缀挂载"""
		server = OpenApiMcpServer(simple_app)

		# 当前为空实现，应该不抛出异常
		server.mount('/custom-mcp')

	def test_mount_with_config_prefix(self, simple_app: FastAPI):
		"""测试使用配置中的前缀"""
		config = OpenApiMcpConfig(prefix='/api/mcp')
		server = OpenApiMcpServer(simple_app, config)

		# 当前为空实现，应该不抛出异常
		server.mount()


class TestEdgeCases:
	"""测试边界情况"""

	def test_empty_app(self):
		"""测试空的 FastAPI 应用"""
		app = FastAPI()
		server = OpenApiMcpServer(app)

		spec = server._get_openapi_spec()
		assert isinstance(spec, dict)
		assert 'paths' in spec
		# 空应用可能有空的 paths 或没有 paths

	def test_app_with_only_root_endpoint(self):
		"""测试只有根路径的应用"""
		app = FastAPI()

		@app.get('/')
		async def root():
			return {'message': 'Hello'}

		server = OpenApiMcpServer(app)
		spec = server._get_openapi_spec()

		assert isinstance(spec, dict)
		assert '/' in spec['paths']

	def test_multiple_servers_with_same_app(self, simple_app: FastAPI):
		"""测试同一个应用创建多个 server 实例"""
		server1 = OpenApiMcpServer(simple_app)
		server2 = OpenApiMcpServer(simple_app)

		spec1 = server1._get_openapi_spec()
		spec2 = server2._get_openapi_spec()

		assert isinstance(spec1, dict)
		assert isinstance(spec2, dict)
		# 两个 server 有独立的缓存
		assert server1.cache is not server2.cache
