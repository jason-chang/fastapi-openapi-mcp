"""
自定义配置示例

展示如何配置 OpenAPI MCP Server 的各种选项，包括缓存、安全、工具过滤等。
"""

from typing import Any

from fastapi import FastAPI
from openapi_mcp.types import ToolDefinition
from pydantic import BaseModel, Field

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import McpServerConfig
from openapi_mcp.security import SecurityFilter


# 创建示例 FastAPI 应用
def create_app() -> FastAPI:
	app = FastAPI(
		title='Custom Config API',
		version='1.0.0',
		description='演示自定义配置的 API',
	)

	class User(BaseModel):
		id: int
		name: str
		email: str
		password: str = Field(..., min_length=8, description='用户密码（敏感信息）')

	class SecretData(BaseModel):
		api_key: str
		secret_token: str
		internal_notes: str

	@app.get('/public/users', tags=['public'])
	async def list_public_users():
		"""公开的用户列表接口"""
		return [
			{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
			{'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
		]

	@app.post('/private/users', tags=['private'])
	async def create_private_user(user: User):
		"""创建用户（包含敏感信息）"""
		return {
			'id': user.id,
			'name': user.name,
			'email': user.email,
			'status': 'created',
		}

	@app.get('/admin/secrets', tags=['admin'])
	async def get_secret_data():
		"""获取敏感数据（管理员接口）"""
		return {
			'api_key': 'sk-1234567890abcdef',
			'secret_token': 'token_secret_123',
			'internal_notes': 'Internal system notes',
		}

	@app.delete('/admin/users/{user_id}', tags=['admin'])
	async def delete_user(user_id: int):
		"""删除用户（危险操作）"""
		return {'message': f'User {user_id} deleted', 'status': 'deleted'}

	return app


# 示例1: 基础自定义配置
def basic_custom_config():
	"""基础自定义配置示例"""
	print('=== 示例1: 基础自定义配置 ===')

	app = create_app()

	# 创建自定义配置
	config = McpServerConfig(
		server_info={'name': 'My Custom MCP Server', 'version': '2.0.0'},
		cache_enabled=True,
		cache_ttl=300,  # 5分钟缓存
		debug=True,
	)

	# 使用自定义配置创建服务器
	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp')

	print('✅ 基础自定义配置服务器已创建')
	print(f'   - 服务器名称: {config.server_info["name"]}')
	print(f'   - 缓存启用: {config.cache_enabled}')
	print(f'   - 缓存TTL: {config.cache_ttl}秒')
	print(f'   - 调试模式: {config.debug}')

	return app, mcp_server


# 示例2: 安全配置
def security_config():
	"""安全配置示例"""
	print('\n=== 示例2: 安全配置 ===')

	app = create_app()

	# 创建自定义安全过滤器
	class CustomSecurityFilter(SecurityFilter):
		def filter_tool(self, tool: ToolDefinition) -> bool:
			# 允许所有工具，但会在数据脱敏中处理敏感信息
			return True

		def filter_data(self, data: Any, context: str = '') -> Any:
			"""自定义数据脱敏逻辑"""
			if isinstance(data, dict):
				# 脱敏敏感字段
				sensitive_keys = [
					'password',
					'api_key',
					'secret_token',
					'internal_notes',
				]
				filtered_data = data.copy()

				for key in sensitive_keys:
					if key in filtered_data:
						if key == 'password':
							filtered_data[key] = '***'
						elif key in ['api_key', 'secret_token']:
							# 保留前几位和后几位
							value = filtered_data[key]
							if len(value) > 8:
								filtered_data[key] = f'{value[:4]}...{value[-4:]}'
							else:
								filtered_data[key] = '***'
						elif key == 'internal_notes':
							filtered_data[key] = '[REDACTED]'

				return filtered_data
			return data

	# 创建带安全配置的服务器
	config = McpServerConfig(
		security_filter=CustomSecurityFilter(),
		access_log_enabled=True,
		audit_sensitive_operations=True,
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-secure')

	print('✅ 安全配置服务器已创建')
	print('   - 自定义数据脱敏规则已应用')
	print('   - 访问日志已启用')
	print('   - 敏感操作审计已启用')

	return app, mcp_server


# 示例3: 工具过滤配置
def tool_filtering_config():
	"""工具过滤配置示例"""
	print('\n=== 示例3: 工具过滤配置 ===')

	app = create_app()

	# 创建工具过滤器
	class ToolFilter:
		def __init__(self, allowed_tags: list[str], blocked_methods: list[str]):
			self.allowed_tags = allowed_tags
			self.blocked_methods = blocked_methods

		def should_include_tool(self, tool_name: str, tool_info: dict) -> bool:
			"""根据工具信息决定是否包含"""
			# 这里简化处理，实际实现会更复杂
			if 'delete' in tool_name.lower():
				return False  # 排除删除操作
			if tool_name == 'generate_examples':
				return True  # 总是包含示例生成
			return True

	ToolFilter(
		allowed_tags=['public', 'users'],  # 只允许这些标签
		blocked_methods=['DELETE'],  # 禁止删除方法
	)

	# 自定义工具配置
	config = McpServerConfig(
		tools_config={
			'search_endpoints': {
				'enabled': True,
				'max_results': 50,  # 限制搜索结果数量
				'cache_enabled': True,
			},
			'generate_examples': {
				'enabled': True,
				'formats': ['json', 'python'],  # 限制示例格式
				'max_examples': 5,
			},
		}
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-filtered')

	print('✅ 工具过滤配置服务器已创建')
	print('   - 删除操作已被过滤')
	print('   - 搜索结果限制为50条')
	print('   - 示例格式限制为 json 和 python')

	return app, mcp_server


# 示例4: 性能优化配置
def performance_config():
	"""性能优化配置示例"""
	print('\n=== 示例4: 性能优化配置 ===')

	app = create_app()

	# 高性能配置
	config = McpServerConfig(
		cache_enabled=True,
		cache_ttl=600,  # 10分钟缓存
		cache_size=1000,  # 最大缓存条目
		max_concurrent_requests=50,  # 最大并发请求数
		request_timeout=30,  # 请求超时时间
		compression_enabled=True,  # 启用压缩
		metrics_enabled=True,  # 启用性能指标
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-fast')

	print('✅ 性能优化配置服务器已创建')
	print(f'   - 缓存TTL: {config.cache_ttl}秒')
	print(f'   - 最大缓存: {config.cache_size}条目')
	print(f'   - 最大并发: {config.max_concurrent_requests}个请求')
	print(f'   - 请求超时: {config.request_timeout}秒')
	print(f'   - 压缩启用: {config.compression_enabled}')
	print(f'   - 指标启用: {config.metrics_enabled}')

	return app, mcp_server


# 示例5: 开发环境配置
def development_config():
	"""开发环境配置示例"""
	print('\n=== 示例5: 开发环境配置 ===')

	app = create_app()

	# 开发环境配置
	config = McpServerConfig(
		debug=True,
		access_log_enabled=True,
		cache_enabled=False,  # 开发时禁用缓存
		mock_data_enabled=True,  # 启用模拟数据
		auto_reload=True,  # 自动重载
		detailed_errors=True,  # 详细错误信息
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-dev')

	print('✅ 开发环境配置服务器已创建')
	print('   - 调试模式已启用')
	print('   - 详细错误信息已启用')
	print('   - 缓存已禁用（便于调试）')
	print('   - 模拟数据已启用')
	print('   - 自动重载已启用')

	return app, mcp_server


# 示例6: 生产环境配置
def production_config():
	"""生产环境配置示例"""
	print('\n=== 示例6: 生产环境配置 ===')

	app = create_app()

	# 生产环境配置
	config = McpServerConfig(
		debug=False,
		cache_enabled=True,
		cache_ttl=1800,  # 30分钟缓存
		access_log_enabled=True,
		security_filter=SecurityFilter(),  # 使用默认安全过滤器
		max_concurrent_requests=100,
		request_timeout=60,
		compression_enabled=True,
		metrics_enabled=True,
		health_check_enabled=True,
		rate_limiting_enabled=True,  # 启用速率限制
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-prod')

	print('✅ 生产环境配置服务器已创建')
	print('   - 调试模式已禁用')
	print('   - 安全过滤器已启用')
	print('   - 速率限制已启用')
	print('   - 健康检查已启用')
	print('   - 所有性能优化选项已启用')

	return app, mcp_server


def main():
	"""运行所有配置示例"""
	print('🔧 OpenAPI MCP 自定义配置演示')
	print('=' * 60)

	# 创建不同的配置示例
	configs = [
		('基础配置', basic_custom_config),
		('安全配置', security_config),
		('工具过滤', tool_filtering_config),
		('性能优化', performance_config),
		('开发环境', development_config),
		('生产环境', production_config),
	]

	apps = []
	servers = []

	for name, config_func in configs:
		try:
			app, server = config_func()
			apps.append(app)
			servers.append(server)
		except Exception as e:
			print(f'❌ {name}配置失败: {e}')

	print(f'\n✅ 成功创建 {len(servers)} 个配置示例')

	# 显示配置总结
	print('\n📊 配置总结:')
	print('   1. 基础配置 - 展示基本自定义选项')
	print('   2. 安全配置 - 演示数据脱敏和访问控制')
	print('   3. 工具过滤 - 展示如何限制可用工具')
	print('   4. 性能优化 - 演示缓存和并发控制')
	print('   5. 开发环境 - 开发友好的配置')
	print('   6. 生产环境 - 生产级安全配置')

	print('\n💡 使用提示:')
	print('   - 根据具体需求选择合适的配置模板')
	print('   - 可以组合多个配置选项')
	print('   - 生产环境建议启用所有安全功能')
	print('   - 开发环境可以禁用缓存便于调试')


if __name__ == '__main__':
	main()
