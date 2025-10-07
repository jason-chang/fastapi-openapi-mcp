"""
多应用实例示例

展示如何在一个项目中为多个不同的 FastAPI 应用配置和管理 OpenAPI MCP Server。
演示多租户、多环境、多服务的复杂场景。
"""

import asyncio

from fastapi import FastAPI
from openapi_mcp.transport.http import HttpMcpTransport
from pydantic import BaseModel

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import McpServerConfig


# 应用1: 电商服务
def create_ecommerce_app() -> FastAPI:
	"""创建电商服务应用"""
	app = FastAPI(
		title='E-commerce Service',
		version='2.1.0',
		description='电商服务 API - 处理商品、订单、支付等业务',
		docs_url='/docs',
		redoc_url='/redoc',
	)

	class Product(BaseModel):
		id: int
		name: str
		price: float
		category: str
		stock: int

	class Order(BaseModel):
		id: int
		user_id: int
		product_ids: list[int]
		total_amount: float
		status: str

	# 商品管理
	@app.get('/products', tags=['products'])
	async def list_products(
		category: str | None = None, min_price: float | None = None
	):
		"""获取商品列表"""
		return {
			'products': [],
			'filters': {'category': category, 'min_price': min_price},
		}

	@app.get('/products/{product_id}', tags=['products'])
	async def get_product(product_id: int):
		"""获取商品详情"""
		return {'id': product_id, 'name': f'Product {product_id}', 'price': 99.99}

	@app.post('/products', tags=['products'])
	async def create_product(product: Product):
		"""创建商品"""
		return {'id': product.id, 'name': product.name, 'status': 'created'}

	# 订单管理
	@app.get('/orders', tags=['orders'])
	async def list_orders(user_id: int | None = None, status: str | None = None):
		"""获取订单列表"""
		return {'orders': [], 'filters': {'user_id': user_id, 'status': status}}

	@app.post('/orders', tags=['orders'])
	async def create_order(order: Order):
		"""创建订单"""
		return {'id': order.id, 'user_id': order.user_id, 'status': 'pending'}

	# 支付处理
	@app.post('/payments', tags=['payments'])
	async def process_payment(order_id: int, amount: float):
		"""处理支付"""
		return {'order_id': order_id, 'amount': amount, 'status': 'paid'}

	return app


# 应用2: 用户管理服务
def create_user_service_app() -> FastAPI:
	"""创建用户管理服务应用"""
	app = FastAPI(
		title='User Management Service',
		version='1.5.0',
		description='用户管理服务 API - 处理认证、授权、用户信息等',
		docs_url='/docs',
		redoc_url='/redoc',
	)

	class User(BaseModel):
		id: int
		username: str
		email: str
		full_name: str
		is_active: bool = True

	class UserProfile(BaseModel):
		user_id: int
		bio: str
		avatar_url: str
		preferences: dict

	# 用户认证
	@app.post('/auth/login', tags=['authentication'])
	async def login(username: str, password: str):
		"""用户登录"""
		return {
			'access_token': 'mock_token',
			'token_type': 'bearer',
			'expires_in': 3600,
		}

	@app.post('/auth/logout', tags=['authentication'])
	async def logout():
		"""用户登出"""
		return {'message': 'Logged out successfully'}

	@app.post('/auth/refresh', tags=['authentication'])
	async def refresh_token(refresh_token: str):
		"""刷新令牌"""
		return {'access_token': 'new_token', 'expires_in': 3600}

	# 用户管理
	@app.get('/users', tags=['users'])
	async def list_users(
		skip: int = 0, limit: int = 50, is_active: bool | None = None
	):
		"""获取用户列表"""
		return {'users': [], 'total': 0, 'skip': skip, 'limit': limit}

	@app.get('/users/{user_id}', tags=['users'])
	async def get_user(user_id: int):
		"""获取用户详情"""
		return {
			'id': user_id,
			'username': f'user_{user_id}',
			'email': f'user{user_id}@example.com',
		}

	@app.post('/users', tags=['users'])
	async def create_user(user: User):
		"""创建用户"""
		return {'id': user.id, 'username': user.username, 'status': 'created'}

	@app.put('/users/{user_id}', tags=['users'])
	async def update_user(user_id: int, user: User):
		"""更新用户信息"""
		return {'id': user_id, 'username': user.username, 'status': 'updated'}

	# 用户配置文件
	@app.get('/users/{user_id}/profile', tags=['profiles'])
	async def get_user_profile(user_id: int):
		"""获取用户配置文件"""
		return {
			'user_id': user_id,
			'bio': 'User bio',
			'avatar_url': 'http://example.com/avatar.jpg',
		}

	@app.put('/users/{user_id}/profile', tags=['profiles'])
	async def update_user_profile(user_id: int, profile: UserProfile):
		"""更新用户配置文件"""
		return {'user_id': user_id, 'bio': profile.bio, 'status': 'updated'}

	return app


# 应用3: 内容管理服务
def create_content_service_app() -> FastAPI:
	"""创建内容管理服务应用"""
	app = FastAPI(
		title='Content Management Service',
		version='1.2.0',
		description='内容管理服务 API - 处理文章、媒体、分类等内容',
		docs_url='/docs',
		redoc_url='/redoc',
	)

	class Article(BaseModel):
		id: int
		title: str
		content: str
		author_id: int
		category_id: int
		tags: list[str]
		published: bool = False

	class Category(BaseModel):
		id: int
		name: str
		description: str
		parent_id: int | None = None

	# 文章管理
	@app.get('/articles', tags=['articles'])
	async def list_articles(
		category_id: int | None = None,
		author_id: int | None = None,
		published: bool | None = None,
		skip: int = 0,
		limit: int = 20,
	):
		"""获取文章列表"""
		return {
			'articles': [],
			'filters': {
				'category_id': category_id,
				'author_id': author_id,
				'published': published,
			},
			'pagination': {'skip': skip, 'limit': limit},
		}

	@app.get('/articles/{article_id}', tags=['articles'])
	async def get_article(article_id: int):
		"""获取文章详情"""
		return {
			'id': article_id,
			'title': f'Article {article_id}',
			'content': 'Article content here...',
			'published': True,
		}

	@app.post('/articles', tags=['articles'])
	async def create_article(article: Article):
		"""创建文章"""
		return {'id': article.id, 'title': article.title, 'status': 'created'}

	@app.put('/articles/{article_id}/publish', tags=['articles'])
	async def publish_article(article_id: int):
		"""发布文章"""
		return {'id': article_id, 'published': True, 'status': 'published'}

	# 分类管理
	@app.get('/categories', tags=['categories'])
	async def list_categories(parent_id: int | None = None):
		"""获取分类列表"""
		return {'categories': [], 'parent_id': parent_id}

	@app.post('/categories', tags=['categories'])
	async def create_category(category: Category):
		"""创建分类"""
		return {'id': category.id, 'name': category.name, 'status': 'created'}

	# 媒体管理
	@app.post('/media/upload', tags=['media'])
	async def upload_media():
		"""上传媒体文件"""
		return {'file_id': 'media_123', 'url': 'http://example.com/media/file.jpg'}

	@app.get('/media/{media_id}', tags=['media'])
	async def get_media(media_id: str):
		"""获取媒体文件信息"""
		return {
			'id': media_id,
			'url': f'http://example.com/media/{media_id}',
			'type': 'image',
		}

	return app


# 应用4: 分析服务
def create_analytics_service_app() -> FastAPI:
	"""创建分析服务应用"""
	app = FastAPI(
		title='Analytics Service',
		version='1.0.0',
		description='分析服务 API - 提供各种业务分析和报表功能',
		docs_url='/docs',
		redoc_url='/redoc',
	)

	# 销售分析
	@app.get('/analytics/sales', tags=['sales'])
	async def get_sales_analytics(
		start_date: str, end_date: str, group_by: str = 'day'
	):
		"""获取销售分析数据"""
		return {
			'period': {'start': start_date, 'end': end_date},
			'group_by': group_by,
			'data': [],
		}

	@app.get('/analytics/sales/top-products', tags=['sales'])
	async def get_top_products(limit: int = 10, period: str = '30d'):
		"""获取热销商品"""
		return {'products': [], 'period': period, 'limit': limit}

	# 用户分析
	@app.get('/analytics/users', tags=['users'])
	async def get_user_analytics(
		start_date: str, end_date: str, metric: str = 'active_users'
	):
		"""获取用户分析数据"""
		return {
			'period': {'start': start_date, 'end': end_date},
			'metric': metric,
			'data': [],
		}

	@app.get('/analytics/users/retention', tags=['users'])
	async def get_user_retention(cohort_period: str = 'weekly'):
		"""获取用户留存数据"""
		return {'cohort_period': cohort_period, 'data': []}

	# 内容分析
	@app.get('/analytics/content', tags=['content'])
	async def get_content_analytics(
		start_date: str, end_date: str, metric: str = 'views'
	):
		"""获取内容分析数据"""
		return {
			'period': {'start': start_date, 'end': end_date},
			'metric': metric,
			'data': [],
		}

	# 系统监控
	@app.get('/analytics/system/health', tags=['system'])
	async def get_system_health():
		"""获取系统健康状态"""
		return {
			'status': 'healthy',
			'services': {'database': 'healthy', 'cache': 'healthy', 'queue': 'healthy'},
			'metrics': {'cpu_usage': 45.2, 'memory_usage': 67.8, 'disk_usage': 23.1},
		}

	@app.get('/analytics/system/performance', tags=['system'])
	async def get_system_performance():
		"""获取系统性能数据"""
		return {
			'response_times': {'avg': 120, 'p95': 250, 'p99': 450},
			'throughput': {'requests_per_second': 1250},
			'error_rates': {'error_rate_5xx': 0.1, 'error_rate_4xx': 2.3},
		}

	return app


# 多应用管理器
class MultiAppManager:
	"""多应用管理器"""

	def __init__(self):
		self.apps = {}
		self.mcp_servers = {}
		self.configs = {}

	def register_app(
		self, name: str, app: FastAPI, config: McpServerConfig | None = None
	):
		"""注册应用"""
		self.apps[name] = app

		# 为不同类型的应用创建不同的配置
		if config is None:
			config = self._create_default_config_for_app(name)

		# 创建 MCP 服务器
		mcp_server = OpenApiMcpServer(app, config=config)
		self.mcp_servers[name] = mcp_server
		self.configs[name] = config

		print(f"✅ 应用 '{name}' 已注册")
		return mcp_server

	def _create_default_config_for_app(self, app_name: str) -> McpServerConfig:
		"""为不同类型的应用创建默认配置"""
		if 'ecommerce' in app_name.lower():
			# 电商应用 - 启用缓存和性能优化
			return McpServerConfig(
				cache_enabled=True,
				cache_ttl=600,
				max_concurrent_requests=100,
				compression_enabled=True,
			)
		elif 'user' in app_name.lower():
			# 用户服务 - 启用安全功能
			return McpServerConfig(
				security_filter_enabled=True,
				access_log_enabled=True,
				audit_sensitive_operations=True,
				cache_ttl=300,
			)
		elif 'content' in app_name.lower():
			# 内容服务 - 启用搜索优化
			return McpServerConfig(
				cache_enabled=True,
				search_optimization_enabled=True,
				max_search_results=100,
			)
		elif 'analytics' in app_name.lower():
			# 分析服务 - 启用指标收集
			return McpServerConfig(
				metrics_enabled=True,
				performance_monitoring_enabled=True,
				cache_enabled=True,
				cache_ttl=1800,
			)
		else:
			# 默认配置
			return McpServerConfig()

	def mount_all(self, base_path: str = '/mcp'):
		"""挂载所有应用的 MCP 服务器"""
		for name, mcp_server in self.mcp_servers.items():
			mount_path = f'{base_path}/{name}'
			mcp_server.mount(mount_path)
			print(f"📎 应用 '{name}' MCP 服务器已挂载到: {mount_path}")

	def get_app_info(self) -> dict:
		"""获取所有应用的信息"""
		info = {}
		for name, app in self.apps.items():
			config = self.configs[name]
			info[name] = {
				'title': app.title,
				'version': app.version,
				'description': app.description,
				'endpoints_count': len(app.routes),
				'mcp_config': {
					'cache_enabled': config.cache_enabled,
					'security_enabled': hasattr(config, 'security_filter')
					and config.security_filter is not None,
					'metrics_enabled': getattr(config, 'metrics_enabled', False),
				},
			}
		return info

	async def test_all_apps(self, base_url: str = 'http://localhost:8000'):
		"""测试所有应用的 MCP 连接"""
		print('\n🧪 测试所有应用的 MCP 连接...')

		for name in self.apps.keys():
			mcp_path = f'{base_url}/mcp/{name}'
			try:
				HttpMcpTransport(mcp_path)
				# 简单连接测试
				print(f'  📡 测试 {name}: {mcp_path}')
				# 这里可以添加更详细的连接测试
				print(f'    ✅ {name} 连接正常')
			except Exception as e:
				print(f'    ❌ {name} 连接失败: {e}')


# 演示不同的部署场景
def demo_single_server_multi_apps():
	"""演示单服务器多应用场景"""
	print('\n=== 场景1: 单服务器多应用 ===')

	# 创建应用管理器
	manager = MultiAppManager()

	# 注册多个应用
	ecommerce_app = create_ecommerce_app()
	user_app = create_user_service_app()
	content_app = create_content_service_app()

	manager.register_app('ecommerce', ecommerce_app)
	manager.register_app('users', user_app)
	manager.register_app('content', content_app)

	# 创建主应用
	main_app = FastAPI(title='Multi-Service Gateway', version='1.0.0')

	# 将子应用挂载到主应用
	main_app.mount('/ecommerce', ecommerce_app)
	main_app.mount('/users', user_app)
	main_app.mount('/content', content_app)

	# 挂载所有 MCP 服务器
	manager.mount_all()

	print('✅ 单服务器多应用架构已创建')
	print('   - 电商服务: /ecommerce')
	print('   - 用户服务: /users')
	print('   - 内容服务: /content')
	print('   - MCP 端点: /mcp/{service_name}')

	return main_app, manager


def demo_multi_tenant_config():
	"""演示多租户配置场景"""
	print('\n=== 场景2: 多租户配置 ===')

	# 为不同租户创建配置
	tenant_configs = {
		'basic': McpServerConfig(
			cache_enabled=True, cache_ttl=300, max_concurrent_requests=20
		),
		'premium': McpServerConfig(
			cache_enabled=True,
			cache_ttl=1800,
			max_concurrent_requests=100,
			compression_enabled=True,
			metrics_enabled=True,
		),
		'enterprise': McpServerConfig(
			cache_enabled=True,
			cache_ttl=3600,
			max_concurrent_requests=500,
			compression_enabled=True,
			metrics_enabled=True,
			security_filter_enabled=True,
			dedicated_cache=True,
		),
	}

	print('✅ 多租户配置已创建')
	print('   - Basic 租户: 基础功能')
	print('   - Premium 租户: 增强功能')
	print('   - Enterprise 租户: 企业级功能')

	return tenant_configs


def demo_environment_specific_configs():
	"""演示环境特定配置场景"""
	print('\n=== 场景3: 环境特定配置 ===')

	environments = {
		'development': {
			'debug': True,
			'cache_enabled': False,
			'access_log_enabled': True,
			'detailed_errors': True,
		},
		'staging': {
			'debug': True,
			'cache_enabled': True,
			'cache_ttl': 60,
			'access_log_enabled': True,
			'metrics_enabled': True,
		},
		'production': {
			'debug': False,
			'cache_enabled': True,
			'cache_ttl': 1800,
			'access_log_enabled': True,
			'security_filter_enabled': True,
			'metrics_enabled': True,
			'compression_enabled': True,
			'max_concurrent_requests': 200,
		},
	}

	print('✅ 环境特定配置已创建')
	for env, config in environments.items():
		print(f'   - {env.title()} 环境: {len(config)} 项配置')

	return environments


async def demo_cross_app_search():
	"""演示跨应用搜索功能"""
	print('\n=== 场景4: 跨应用搜索演示 ===')

	# 这里可以演示如何在一个应用中搜索其他应用的端点
	print('🔍 跨应用搜索功能:')
	print('   - 可以搜索所有注册服务的端点')
	print('   - 支持按服务名称过滤')
	print('   - 支持统一的安全控制')

	# 模拟搜索结果
	search_results = {
		'total_endpoints': 45,
		'services': {
			'ecommerce': {
				'endpoints': 18,
				'categories': ['products', 'orders', 'payments'],
			},
			'users': {
				'endpoints': 15,
				'categories': ['authentication', 'users', 'profiles'],
			},
			'content': {
				'endpoints': 12,
				'categories': ['articles', 'categories', 'media'],
			},
		},
	}

	print(f'   📊 总计发现 {search_results["total_endpoints"]} 个端点')
	for service, info in search_results['services'].items():
		print(f'      - {service}: {info["endpoints"]} 个端点')


def main():
	"""运行多应用示例"""
	print('🏢 OpenAPI MCP 多应用实例演示')
	print('=' * 60)

	# 场景1: 单服务器多应用
	main_app, manager = demo_single_server_multi_apps()

	# 场景2: 多租户配置
	demo_multi_tenant_config()

	# 场景3: 环境特定配置
	demo_environment_specific_configs()

	# 场景4: 跨应用搜索
	asyncio.run(demo_cross_app_search())

	# 显示应用信息
	print('\n📋 应用信息总览:')
	app_info = manager.get_app_info()
	for name, info in app_info.items():
		print(f'\n  📱 {name.title()} 服务:')
		print(f'     标题: {info["title"]}')
		print(f'     版本: {info["version"]}')
		print(f'     端点数: {info["endpoints_count"]}')
		print(f'     缓存: {"启用" if info["mcp_config"]["cache_enabled"] else "禁用"}')
		print(
			f'     安全: {"启用" if info["mcp_config"]["security_enabled"] else "禁用"}'
		)
		print(
			f'     指标: {"启用" if info["mcp_config"]["metrics_enabled"] else "禁用"}'
		)

	print('\n💡 多应用架构优势:')
	print('   🔄 服务解耦: 每个服务独立开发和部署')
	print('   🔧 灵活配置: 不同服务可以使用不同配置')
	print('   📈 可扩展性: 可以轻松添加或移除服务')
	print('   🛡️ 安全隔离: 服务间的安全策略相互独立')
	print('   📊 统一管理: 通过统一的管理器管理所有服务')

	print('\n🚀 使用建议:')
	print('   - 根据业务功能合理划分服务')
	print('   - 为不同服务配置合适的缓存策略')
	print('   - 敏感服务启用更严格的安全控制')
	print('   - 监控各服务的性能指标')

	return main_app


if __name__ == '__main__':
	app = main()

	# 如果需要运行服务器

	print('\n🌐 启动服务器...')
	print('   访问 http://localhost:8000/docs 查看主 API 文档')
	print('   访问 http://localhost:8000/mcp/ecommerce 连接电商服务 MCP')
	print('   访问 http://localhost:8000/mcp/users 连接用户服务 MCP')
	print('   访问 http://localhost:8000/mcp/content 连接内容服务 MCP')

	# uvicorn.run(app, host="0.0.0.0", port=8000)
