"""
MCP Server stdio 连接示例

演示如何通过 stdio 协议与 MCP Server 通信。
适用于命令行工具和 IDE 集成。
"""

import asyncio
import json
import sys

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpServer


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


async def handle_stdio_rpc():
	"""处理 stdio JSON-RPC 请求"""
	# 创建应用和 MCP Server
	app = create_test_app()
	mcp_server = OpenApiMcpServer(app)

	# 获取所有工具
	tools = mcp_server.tools

	# 输出初始化消息到 stderr（调试用）
	print(f'✅ MCP Server 初始化成功，共 {len(tools)} 个工具', file=sys.stderr)

	# 读取 stdin 的 JSON-RPC 请求
	for line in sys.stdin:
		try:
			request = json.loads(line.strip())
			method = request.get('method')
			params = request.get('params', {})
			request_id = request.get('id')

			# 处理不同的方法
			if method == 'initialize':
				# 初始化
				response = {
					'jsonrpc': '2.0',
					'id': request_id,
					'result': {
						'protocolVersion': '2025-06-18',
						'capabilities': {
							'tools': {},
						},
						'serverInfo': {
							'name': 'openapi-mcp-server',
							'version': '0.1.0',
						},
					},
				}

			elif method == 'tools/list':
				# 列出所有工具
				tool_list = []
				for tool in tools:
					tool_list.append(
						{
							'name': tool.name,
							'description': tool.description,
							'inputSchema': tool.input_schema or {'type': 'object'},
						}
					)

				response = {
					'jsonrpc': '2.0',
					'id': request_id,
					'result': {'tools': tool_list},
				}

			elif method == 'tools/call':
				# 调用工具
				tool_name = params.get('name')
				tool_params = params.get('arguments', {})

				# 查找工具
				tool = next((t for t in tools if t.name == tool_name), None)

				if tool:
					# 执行工具
					result = await tool.execute(**tool_params)

					# 转换结果格式
					response = {
						'jsonrpc': '2.0',
						'id': request_id,
						'result': {
							'content': [
								{
									'type': c.type,
									'text': c.text,
								}
								for c in result.content
							],
						},
					}
				else:
					response = {
						'jsonrpc': '2.0',
						'id': request_id,
						'error': {
							'code': -32601,
							'message': f'Tool not found: {tool_name}',
						},
					}

			else:
				# 未知方法
				response = {
					'jsonrpc': '2.0',
					'id': request_id,
					'error': {
						'code': -32601,
						'message': f'Method not found: {method}',
					},
				}

			# 输出响应
			print(json.dumps(response), flush=True)

		except json.JSONDecodeError as e:
			print(
				json.dumps(
					{
						'jsonrpc': '2.0',
						'id': None,
						'error': {'code': -32700, 'message': f'Parse error: {e}'},
					}
				),
				flush=True,
			)
		except Exception as e:
			print(f'❌ 错误: {e}', file=sys.stderr)
			print(
				json.dumps(
					{
						'jsonrpc': '2.0',
						'id': request.get('id') if 'request' in locals() else None,
						'error': {'code': -32603, 'message': f'Internal error: {e}'},
					}
				),
				flush=True,
			)


if __name__ == '__main__':
	# 运行异步事件循环
	asyncio.run(handle_stdio_rpc())
