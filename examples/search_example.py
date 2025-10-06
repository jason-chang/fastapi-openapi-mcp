"""
使用 SearchEndpointsTool 的示例

演示如何使用搜索功能快速找到所需的 API 接口。
"""

import asyncio

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpServer


def create_sample_app() -> FastAPI:
	"""创建示例 FastAPI 应用"""
	app = FastAPI(
		title='电商 API',
		version='1.0.0',
		description='一个示例电商 API 系统',
	)

	# 用户相关接口
	@app.get('/api/v1/users', tags=['users'], summary='列出所有用户')
	async def list_users():
		"""获取系统中所有用户的列表"""
		return {'users': []}

	@app.post('/api/v1/users', tags=['users'], summary='创建新用户')
	async def create_user():
		"""向系统添加新用户"""
		return {'id': 1}

	@app.get('/api/v1/users/{user_id}', tags=['users'], summary='获取用户详情')
	async def get_user(user_id: int):
		"""根据用户 ID 获取特定用户的详细信息"""
		return {'id': user_id, 'name': 'John Doe'}

	# 商品相关接口
	@app.get('/api/v1/products', tags=['products'], summary='列出所有商品')
	async def list_products():
		"""获取商店中所有商品的列表"""
		return {'products': []}

	@app.post('/api/v1/products', tags=['products'], summary='创建新商品')
	async def create_product():
		"""添加新商品到商店"""
		return {'id': 1}

	@app.get('/api/v1/products/{product_id}', tags=['products'], summary='获取商品详情')
	async def get_product(product_id: int):
		"""根据商品 ID 获取特定商品的详细信息"""
		return {'id': product_id, 'name': 'Sample Product'}

	# 订单相关接口
	@app.get('/api/v1/orders', tags=['orders'], summary='列出所有订单')
	async def list_orders():
		"""获取系统中所有订单的列表"""
		return {'orders': []}

	@app.post('/api/v1/orders', tags=['orders'], summary='创建新订单')
	async def create_order():
		"""创建新订单"""
		return {'id': 1}

	return app


async def main():
	"""主函数：演示 SearchEndpointsTool 的各种用法"""
	# 创建 FastAPI 应用
	app = create_sample_app()

	# 创建 MCP Server
	mcp_server = OpenApiMcpServer(app)

	# 获取所有已注册的工具
	tools = mcp_server.get_registered_tools()
	print(f'✅ 已注册 {len(tools)} 个 MCP Tools\n')

	# 获取 SearchEndpointsTool（第 5 个工具）
	search_tool = tools[4]
	print(f'🔍 使用工具: {search_tool.name}\n')

	# 示例 1: 在路径中搜索 'users'
	print('=' * 60)
	print('示例 1: 在路径中搜索 "users"')
	print('=' * 60)
	result1 = await search_tool.execute(keyword='users', search_in='path')
	print(result1.content[0].text)
	print()

	# 示例 2: 在摘要中搜索 '商品'
	print('=' * 60)
	print('示例 2: 在摘要中搜索 "商品"')
	print('=' * 60)
	result2 = await search_tool.execute(keyword='商品', search_in='summary')
	print(result2.content[0].text)
	print()

	# 示例 3: 全范围搜索 'create'
	print('=' * 60)
	print('示例 3: 全范围搜索 "create"')
	print('=' * 60)
	result3 = await search_tool.execute(keyword='create', search_in='all')
	print(result3.content[0].text)
	print()

	# 示例 4: 搜索不存在的关键词
	print('=' * 60)
	print('示例 4: 搜索不存在的关键词 "payment"')
	print('=' * 60)
	result4 = await search_tool.execute(keyword='payment', search_in='all')
	print(result4.content[0].text)
	print()

	# 示例 5: 使用默认搜索范围（all）
	print('=' * 60)
	print('示例 5: 使用默认搜索范围搜索 "v1"')
	print('=' * 60)
	result5 = await search_tool.execute(keyword='v1')
	print(result5.content[0].text)
	print()

	print('✅ 所有示例运行完成！')


if __name__ == '__main__':
	asyncio.run(main())
