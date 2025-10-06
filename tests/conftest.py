"""
Pytest 配置和共享 fixtures
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import OpenApiMcpConfig


@pytest.fixture
def sample_app() -> FastAPI:
	"""创建一个简单的 FastAPI 应用用于测试"""
	app = FastAPI(title='Test API', version='1.0.0')

	@app.get('/users', tags=['users'])
	async def list_users():
		"""列出所有用户"""
		return {'users': []}

	@app.post('/users', tags=['users'])
	async def create_user():
		"""创建用户"""
		return {'id': 1}

	@app.get('/items/{item_id}', tags=['items'])
	async def get_item(item_id: int):
		"""获取单个项目"""
		return {'id': item_id}

	return app


@pytest.fixture
def mcp_config() -> OpenApiMcpConfig:
	"""创建测试用 MCP 配置"""
	return OpenApiMcpConfig(
		cache_enabled=False,  # 测试时禁用缓存
		output_format='markdown',
		allowed_origins=['http://localhost', 'http://127.0.0.1', 'http://test.com'],
	)


@pytest.fixture
def mcp_server(sample_app: FastAPI, mcp_config: OpenApiMcpConfig) -> OpenApiMcpServer:
	"""创建 MCP Server 实例并挂载路由"""
	server = OpenApiMcpServer(sample_app, config=mcp_config)
	server.mount('/mcp')  # 挂载 MCP 端点
	return server


@pytest.fixture
async def async_client(sample_app: FastAPI):
	"""创建异步 HTTP 客户端用于测试"""
	transport = ASGITransport(app=sample_app)
	async with AsyncClient(transport=transport, base_url='http://test') as client:
		yield client
