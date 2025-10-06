"""
自定义配置示例

展示如何使用自定义配置来控制 MCP Server 的行为。
"""

from typing import Any

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpConfig, OpenApiMcpServer

app = FastAPI(title='My API', version='1.0.0', description='带有自定义配置的 API')


@app.get('/users', tags=['users'])
async def list_users():
	"""列出所有用户"""
	return {'users': []}


@app.post('/users', tags=['users'])
async def create_user():
	"""创建用户"""
	return {'id': 1}


@app.get('/internal/health')
async def health_check():
	"""内部健康检查接口，不想暴露给 AI"""
	return {'status': 'ok'}


# 定义 tool 过滤器
def tool_filter(path: str, _method: str, _endpoint_info: dict[str, Any]) -> bool:
	"""过滤内部接口

	Args:
		path: 接口路径
		_method: HTTP 方法（未使用）
		_endpoint_info: 接口详细信息（未使用）

	Returns:
		True 表示保留该接口，False 表示过滤掉
	"""
	# 过滤所有 /internal/ 开头的接口
	if path.startswith('/internal/'):
		return False
	return True


# 自定义配置
config = OpenApiMcpConfig(
	cache_enabled=True,
	cache_ttl=600,  # 缓存 10 分钟
	prefix='/api-mcp',  # 自定义路由前缀
	output_format='markdown',  # 输出格式：markdown, json, plain
	max_output_length=15000,  # 最大输出长度
	tool_filter=tool_filter,  # 使用自定义过滤器
	include_sse=True,  # 包含 SSE 端点
	include_rest_api=True,  # 包含 REST API（调试用）
)

# 使用自定义配置创建 MCP Server
mcp_server = OpenApiMcpServer(app, config=config)
mcp_server.mount()

if __name__ == '__main__':
	import uvicorn

	# 运行应用
	# MCP 端点将在 /api-mcp 路径下
	uvicorn.run(app, host='0.0.0.0', port=8000)
