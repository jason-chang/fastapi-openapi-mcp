"""
基础使用示例

展示如何在 FastAPI 应用中集成 OpenAPI MCP Server。
"""

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpServer

# 创建 FastAPI 应用
app = FastAPI(
	title='My Awesome API',
	version='1.0.0',
	description='这是一个展示如何使用 OpenAPI MCP Server 的示例 API',
)


@app.get('/users', tags=['users'])
async def list_users():
	"""列出所有用户"""
	return {'users': []}


@app.post('/users', tags=['users'])
async def create_user():
	"""创建用户"""
	return {'id': 1, 'name': 'John Doe'}


@app.get('/items/{item_id}', tags=['items'])
async def get_item(item_id: int):
	"""获取单个项目"""
	return {'id': item_id, 'name': f'Item {item_id}'}


# 集成 MCP Server（使用默认配置）
mcp_server = OpenApiMcpServer(app)
mcp_server.mount('/mcp')

if __name__ == '__main__':
	import uvicorn

	# 运行应用
	# 访问 http://localhost:8000/docs 查看 API 文档
	uvicorn.run(app, host='0.0.0.0', port=8000)
