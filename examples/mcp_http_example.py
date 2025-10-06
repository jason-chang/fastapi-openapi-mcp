"""
MCP Server StreamableHTTP 连接示例

演示如何通过 HTTP 协议与 MCP Server 通信。
适用于 Web 应用和远程服务集成。
"""

import asyncio
import json

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import OpenApiMcpConfig


def create_test_app() -> FastAPI:
	"""创建测试用的 FastAPI 应用"""
	app = FastAPI(
		title='OpenAPI MCP Test API',
		version='1.0.0',
		description='用于测试 OpenAPI MCP Server 的示例 API',
		openapi_tags=[
			{'name': 'users', 'description': '用户管理接口'},
			{'name': 'items', 'description': '商品管理接口'},
		],
		port=8888,
	)

	# 用户接口
	@app.get('/users', tags=['users'], summary='获取用户列表')
	async def list_users(skip: int = 0, limit: int = 10):
		"""获取所有用户（分页）"""
		return {
			'users': [
				{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
				{'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
			],
			'total': 2,
			'skip': skip,
			'limit': limit,
		}

	@app.post('/users', tags=['users'], summary='创建新用户', status_code=201)
	async def create_user(name: str, email: str):
		"""创建新用户"""
		return {'id': 3, 'name': name, 'email': email, 'created': True}

	@app.get('/users/{user_id}', tags=['users'], summary='获取用户详情')
	async def get_user(user_id: int):
		"""获取指定用户的详细信息"""
		return {
			'id': user_id,
			'name': 'Alice',
			'email': 'alice@example.com',
			'role': 'admin',
		}

	# 商品接口
	@app.get('/items', tags=['items'], summary='获取商品列表')
	async def list_items(category: str | None = None):
		"""获取所有商品，可按分类筛选"""
		items = [
			{'id': 1, 'name': 'Laptop', 'price': 999.99, 'category': 'electronics'},
			{'id': 2, 'name': 'Mouse', 'price': 29.99, 'category': 'electronics'},
		]
		# 如果指定了分类，进行过滤
		if category:
			items = [item for item in items if item['category'] == category]
		return {'items': items}

	@app.get('/items/{item_id}', tags=['items'], summary='获取商品详情')
	async def get_item(item_id: int):
		"""获取指定商品的详细信息"""
		return {
			'id': item_id,
			'name': 'Laptop',
			'price': 999.99,
			'category': 'electronics',
			'stock': 10,
		}

	return app


def create_mcp_http_server() -> FastAPI:
	"""创建带有 MCP Server 的 FastAPI 应用"""
	# 创建基础应用
	app = create_test_app()

	# 添加 CORS 中间件以支持 MCP Inspector 连接
	app.add_middleware(
		CORSMiddleware,
		allow_origins=['*'],  # 允许所有来源
		allow_credentials=True,
		allow_methods=['*'],  # 允许所有方法
		allow_headers=['*'],  # 允许所有头部
	)

	config = OpenApiMcpConfig(
		cache_enabled=True,
		cache_ttl=300,
		prefix='/openapi-mcp',
		include_sse=True,
		include_rest_api=True,
		output_format='json',
		max_output_length=10000,
		custom_tools=[],
		tool_filter=None,
		auth_required=False,
		allowed_origins=['*'],
		enable_access_logging=False,
		mask_sensitive_data=True,
		path_patterns=[],
		allowed_tags=[],
		blocked_tags=[],
	)
	# 创建 MCP Server 并挂载到 /mcp 端点
	mcp_server = OpenApiMcpServer(app, config)
	mcp_server.mount('/openapi-mcp')

	# 添加一个简单的根路由，用于测试
	@app.get('/')
	async def root():
		"""根路由，返回基本信息"""
		return {
			'message': 'OpenAPI MCP Server HTTP Example',
			'mcp_endpoint': '/mcp',
			'openapi_docs': '/openapi.json',
			'swagger_ui': '/docs',
		}

	return app


async def test_mcp_http_client():
	"""测试 MCP HTTP 客户端"""
	import httpx

	# 测试数据
	base_url = 'http://localhost:8000'
	mcp_url = f'{base_url}/mcp'

	async with httpx.AsyncClient() as client:
		print('🧪 测试 MCP HTTP 连接...\n')

		# 1. 测试初始化
		print('📝 测试 1: Initialize')
		init_request = {
			'jsonrpc': '2.0',
			'id': 1,
			'method': 'initialize',
			'params': {
				'capabilities': {'tools': {}},
			},
		}

		response = await client.post(
			mcp_url,
			json=init_request,
			headers={'Mcp-Protocol-Version': '2025-06-18'},
		)

		if response.status_code == 200:
			result = response.json()
			session_id = response.headers.get('Mcp-Session-Id')
			print(f'✅ 初始化成功，会话 ID: {session_id}')
			print(f'   服务器信息: {result["result"]["serverInfo"]}\n')
		else:
			print(f'❌ 初始化失败: {response.status_code} {response.text}')
			return

		# 2. 测试工具列表
		print('📝 测试 2: List Tools')
		tools_request = {
			'jsonrpc': '2.0',
			'id': 2,
			'method': 'tools/list',
			'params': {},
		}

		response = await client.post(
			mcp_url,
			json=tools_request,
			headers={
				'Mcp-Protocol-Version': '2025-06-18',
				'Mcp-Session-Id': session_id,
			},
		)

		if response.status_code == 200:
			result = response.json()
			tools = result['result']['tools']
			print(f'✅ 获取工具列表成功，共 {len(tools)} 个工具')
			for tool in tools[:3]:  # 只显示前3个
				print(f'   - {tool["name"]}: {tool["description"]}')
			print('   ...\n')
		else:
			print(f'❌ 获取工具列表失败: {response.status_code} {response.text}')
			return

		# 3. 测试调用工具
		print('📝 测试 3: Call Tool - list_openapi_endpoints')
		call_request = {
			'jsonrpc': '2.0',
			'id': 3,
			'method': 'tools/call',
			'params': {
				'name': 'list_openapi_endpoints',
				'arguments': {},
			},
		}

		response = await client.post(
			mcp_url,
			json=call_request,
			headers={
				'Mcp-Protocol-Version': '2025-06-18',
				'Mcp-Session-Id': session_id,
			},
		)

		if response.status_code == 200:
			result = response.json()
			content = result['result']['content'][0]['text']
			print('✅ 调用工具成功')
			print('   接口列表（前200字符）:')
			print(f'   {content[:200]}...\n')
		else:
			print(f'❌ 调用工具失败: {response.status_code} {response.text}')
			return

		# 4. 测试 SSE 流
		print('📝 测试 4: SSE Stream')
		try:
			async with client.stream(
				'GET',
				mcp_url,
				headers={
					'Mcp-Protocol-Version': '2025-06-18',
					'Mcp-Session-Id': session_id,
					'Accept': 'text/event-stream',
				},
				timeout=10.0,
			) as response:
				if response.status_code == 200:
					print('✅ SSE 流连接成功')
					print('   接收前3个事件:')
					count = 0
					async for line in response.aiter_lines():
						if line.startswith('data: '):
							data = json.loads(line[6:])
							print(f'   事件数据: {data}')
							count += 1
							if count >= 3:
								break
				else:
					print(f'❌ SSE 流连接失败: {response.status_code}')
		except Exception as e:
			print(f'❌ SSE 流测试失败: {e}')

		# 5. 清理会话
		print('\n📝 测试 5: Delete Session')
		response = await client.delete(
			mcp_url,
			headers={
				'Mcp-Protocol-Version': '2025-06-18',
				'Mcp-Session-Id': session_id,
			},
		)

		if response.status_code == 204:
			print('✅ 会话删除成功')
		else:
			print(f'❌ 会话删除失败: {response.status_code}')

		print('\n✅ 所有测试完成！')


if __name__ == '__main__':
	import sys

	if len(sys.argv) > 1 and sys.argv[1] == 'test':
		# 运行测试客户端
		asyncio.run(test_mcp_http_client())
	else:
		# 启动 HTTP 服务器
		app = create_mcp_http_server()

		print('🚀 启动 OpenAPI MCP HTTP 服务器...')
		print('📍 MCP 端点: http://localhost:8888/mcp')
		print('📖 API 文档: http://localhost:8888/docs')
		print('🧪 运行测试: python mcp_http_example.py test')
		print('')

		uvicorn.run(app, host='0.0.0.0', port=8888)
