"""
Resources + Tools 综合使用示例

展示如何同时使用 Resources 和 Tools 功能来探索和操作 OpenAPI 规范。
这个示例展示了 MCP 2025-06-18 标准的混合架构优势。
"""

import asyncio
import json

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.client import OpenApiMcpClient
from openapi_mcp.transport.http import HttpMcpTransport


# 创建一个更丰富的示例 FastAPI 应用
def create_demo_app() -> FastAPI:
	"""创建演示用的 FastAPI 应用"""
	app = FastAPI(
		title='E-commerce API',
		version='2.1.0',
		description='一个完整的电商 API 示例，展示 Resources 和 Tools 的协同工作',
	)

	# 用户管理端点
	@app.get('/users', tags=['users'])
	async def list_users(skip: int = 0, limit: int = 50):
		"""获取用户列表，支持分页"""
		return {'users': [], 'total': 0, 'skip': skip, 'limit': limit}

	@app.get('/users/{user_id}', tags=['users'])
	async def get_user(user_id: int):
		"""获取特定用户详情"""
		return {
			'id': user_id,
			'name': f'User {user_id}',
			'email': f'user{user_id}@example.com',
		}

	@app.post('/users', tags=['users'])
	async def create_user(user_data: dict):
		"""创建新用户"""
		return {'id': 123, 'name': user_data.get('name'), 'status': 'created'}

	# 产品管理端点
	@app.get('/products', tags=['products'])
	async def list_products(category: str = None, min_price: float = None):
		"""获取产品列表，支持分类和价格筛选"""
		return {
			'products': [],
			'filters': {'category': category, 'min_price': min_price},
		}

	@app.get('/products/{product_id}', tags=['products'])
	async def get_product(product_id: int):
		"""获取产品详情"""
		return {
			'id': product_id,
			'name': f'Product {product_id}',
			'price': 99.99,
			'category': 'electronics',
			'description': 'A great product',
		}

	# 订单管理端点
	@app.get('/orders', tags=['orders'])
	async def list_orders(user_id: int = None, status: str = None):
		"""获取订单列表"""
		return {'orders': [], 'filters': {'user_id': user_id, 'status': status}}

	@app.post('/orders', tags=['orders'])
	async def create_order(order_data: dict):
		"""创建新订单"""
		return {'id': 456, 'user_id': order_data.get('user_id'), 'status': 'pending'}

	return app


class ResourcesToolsDemo:
	"""Resources + Tools 综合使用演示类"""

	def __init__(self, base_url: str = 'http://localhost:8000'):
		self.base_url = base_url
		self.client = None
		self.transport = None

	async def __aenter__(self):
		"""异步上下文管理器入口"""
		self.transport = HttpMcpTransport(self.base_url + '/mcp')
		self.client = OpenApiMcpClient(self.transport)
		await self.transport.connect()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""异步上下文管理器出口"""
		if self.transport:
			await self.transport.disconnect()

	async def demo_resources_discovery(self):
		"""演示 Resources 发现功能"""
		print('\n=== Resources 发现演示 ===')

		# 1. 列出所有可用的 Resources
		print('\n1. 获取所有可用 Resources:')
		resources = await self.client.list_resources()
		for resource in resources:
			print(f'  - {resource.uri}: {resource.name}')

		return resources

	async def demo_resources_reading(self, resources):
		"""演示 Resources 读取功能"""
		print('\n=== Resources 读取演示 ===')

		# 2. 读取完整 OpenAPI 规范
		print('\n2. 读取完整 OpenAPI 规范:')
		spec_resource = next((r for r in resources if r.uri == 'openapi://spec'), None)
		if spec_resource:
			spec_content = await self.client.read_resource(spec_resource.uri)
			spec = json.loads(spec_content)
			print(f'  - API 标题: {spec.get("info", {}).get("title")}')
			print(f'  - API 版本: {spec.get("info", {}).get("version")}')
			print(f'  - 端点总数: {len(spec.get("paths", {}))}')

		# 3. 读取端点列表
		print('\n3. 读取端点列表:')
		endpoints_resource = next(
			(r for r in resources if r.uri == 'openapi://endpoints'), None
		)
		if endpoints_resource:
			endpoints_content = await self.client.read_resource(endpoints_resource.uri)
			endpoints = json.loads(endpoints_content)
			print(f'  - 总端点数: {len(endpoints)}')
			for endpoint in endpoints[:3]:  # 显示前3个端点
				print(
					f'    * {endpoint["method"]} {endpoint["path"]} - {endpoint["summary"]}'
				)

		# 4. 读取模型列表
		print('\n4. 读取数据模型列表:')
		models_resource = next(
			(r for r in resources if r.uri == 'openapi://models'), None
		)
		if models_resource:
			models_content = await self.client.read_resource(models_resource.uri)
			models = json.loads(models_content)
			print(f'  - 总模型数: {len(models)}')
			for model in models[:3]:  # 显示前3个模型
				print(
					f'    * {model["name"]}: {model.get("description", "No description")}'
				)

		# 5. 读取标签信息
		print('\n5. 读取标签分组:')
		tags_resource = next((r for r in resources if r.uri == 'openapi://tags'), None)
		if tags_resource:
			tags_content = await self.client.read_resource(tags_resource.uri)
			tags = json.loads(tags_content)
			print(f'  - 总标签数: {len(tags)}')
			for tag in tags:
				print(
					f'    * {tag["name"]}: {tag.get("description", "No description")} ({tag["endpoint_count"]} 个端点)'
				)

	async def demo_tools_searching(self):
		"""演示 Tools 搜索功能"""
		print('\n=== Tools 搜索演示 ===')

		# 6. 使用 search_endpoints 工具进行复杂搜索
		print('\n6. 搜索用户相关的端点:')
		search_result = await self.client.call_tool(
			'search_endpoints',
			{
				'query': 'user',
				'filters': {'methods': ['GET', 'POST'], 'tags': ['users']},
			},
		)
		print(f'  - 找到 {len(search_result["results"])} 个用户相关端点')
		for result in search_result['results']:
			print(f'    * {result["method"]} {result["path"]}: {result["summary"]}')

		# 7. 搜索特定价格范围的产品端点
		print('\n7. 搜索产品相关端点:')
		search_result = await self.client.call_tool(
			'search_endpoints', {'query': 'product', 'pattern': r'products?/.*'}
		)
		print(f'  - 找到 {len(search_result["results"])} 个产品相关端点')

		# 8. 按标签搜索订单端点
		print('\n8. 搜索订单相关端点:')
		search_result = await self.client.call_tool(
			'search_endpoints', {'filters': {'tags': ['orders']}}
		)
		print(f'  - 找到 {len(search_result["results"])} 个订单相关端点')

	async def demo_tools_examples(self):
		"""演示 Tools 示例生成功能"""
		print('\n=== Tools 示例生成演示 ===')

		# 9. 为创建用户端点生成示例
		print('\n9. 为 POST /users 生成调用示例:')
		example_result = await self.client.call_tool(
			'generate_examples',
			{
				'endpoint_path': '/users',
				'method': 'POST',
				'formats': ['json', 'curl', 'python'],
			},
		)

		examples = example_result['examples']
		print('  - JSON 示例:')
		print(f'    {json.dumps(examples["json"], indent=6)}')

		print('  - cURL 示例:')
		print(f'    {examples["curl"]}')

		# 10. 为带参数的端点生成示例
		print('\n10. 为 GET /products 生成带参数的示例:')
		example_result = await self.client.call_tool(
			'generate_examples',
			{
				'endpoint_path': '/products',
				'method': 'GET',
				'include_parameters': True,
				'formats': ['python'],
			},
		)

		print('  - Python 示例:')
		print(f'    {example_result["examples"]["python"]}')

	async def demo_mixed_workflow(self):
		"""演示 Resources + Tools 混合工作流"""
		print('\n=== Resources + Tools 混合工作流演示 ===')

		# 11. 使用 Resources 了解整体结构，然后用 Tools 进行精确操作
		print('\n11. 混合工作流：探索 -> 搜索 -> 生成示例')

		# 步骤1: 用 Resources 获取标签概览
		resources = await self.client.list_resources()
		tags_resource = next((r for r in resources if r.uri == 'openapi://tags'), None)
		tags_content = await self.client.read_resource(tags_resource.uri)
		tags = json.loads(tags_content)

		# 步骤2: 选择一个感兴趣的标签（比如 products）
		products_tag = next((tag for tag in tags if tag['name'] == 'products'), None)
		if products_tag:
			print(
				f'  - 发现产品标签: {products_tag["name"]} ({products_tag["endpoint_count"]} 个端点)'
			)

			# 步骤3: 用 Tools 搜索该标签下的所有端点
			search_result = await self.client.call_tool(
				'search_endpoints', {'filters': {'tags': ['products']}}
			)

			# 步骤4: 为每个端点生成示例
			for result in search_result['results']:
				print(f'\n    为 {result["method"]} {result["path"]} 生成示例:')
				example_result = await self.client.call_tool(
					'generate_examples',
					{
						'endpoint_path': result['path'],
						'method': result['method'],
						'formats': ['json'],
					},
				)
				print(
					f'      {json.dumps(example_result["examples"]["json"], indent=8)}'
				)


async def main():
	"""主演示函数"""
	print('🚀 OpenAPI MCP Resources + Tools 综合使用演示')
	print('=' * 60)

	# 创建并启动演示应用
	app = create_demo_app()

	# 集成 MCP Server
	mcp_server = OpenApiMcpServer(app)
	mcp_server.mount('/mcp')

	# 在后台运行 FastAPI 应用
	import threading

	import uvicorn

	def run_server():
		uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')

	server_thread = threading.Thread(target=run_server, daemon=True)
	server_thread.start()

	# 等待服务器启动
	await asyncio.sleep(2)

	# 运行演示
	async with ResourcesToolsDemo() as demo:
		try:
			# 资源发现
			resources = await demo.demo_resources_discovery()

			# 资源读取
			await demo.demo_resources_reading(resources)

			# 工具搜索
			await demo.demo_tools_searching()

			# 示例生成
			await demo.demo_tools_examples()

			# 混合工作流
			await demo.demo_mixed_workflow()

			print('\n' + '=' * 60)
			print('✅ 演示完成！')
			print('\n💡 关键要点:')
			print('   - Resources 提供结构化的 API 概览和导航')
			print('   - Tools 提供强大的搜索和示例生成功能')
			print('   - 两者结合可以实现完整的 API 探索和使用流程')

		except Exception as e:
			print(f'❌ 演示过程中出现错误: {e}')
			import traceback

			traceback.print_exc()


if __name__ == '__main__':
	asyncio.run(main())
