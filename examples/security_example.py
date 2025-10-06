"""
安全功能使用示例

演示如何使用工具过滤器、敏感信息脱敏和访问日志记录。
"""

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpConfig, OpenApiMcpServer

# 创建 FastAPI 应用
app = FastAPI(title='安全示例 API', version='1.0.0')


# 定义 API 接口
@app.get('/api/public/users', tags=['public'])
async def list_public_users():
	"""列出公开用户（任何人都可以访问）"""
	return {'users': [{'id': 1, 'name': 'alice'}, {'id': 2, 'name': 'bob'}]}


@app.get('/api/admin/users', tags=['admin'])
async def list_admin_users():
	"""列出所有用户（仅管理员可以访问）"""
	return {
		'users': [
			{'id': 1, 'name': 'alice', 'password': 'secret1', 'token': 'token123'},
			{'id': 2, 'name': 'bob', 'password': 'secret2', 'token': 'token456'},
		]
	}


@app.post('/api/auth/login', tags=['auth'])
async def login():
	"""用户登录"""
	return {'token': 'jwt_token_abc', 'refresh_token': 'refresh_xyz'}


# 示例 1: 基本配置 - 启用敏感数据脱敏
def example_basic_masking():
	"""示例 1: 启用敏感数据脱敏"""
	print('\n=== 示例 1: 基本敏感数据脱敏 ===')

	config = OpenApiMcpConfig(
		mask_sensitive_data=True,  # 启用敏感数据脱敏
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，启用敏感数据脱敏')
	print('✓ 敏感字段（password、token 等）将被自动脱敏为 ***')


# 示例 2: 路径过滤 - 只允许访问公开接口
def example_path_filter():
	"""示例 2: 使用路径模式过滤"""
	print('\n=== 示例 2: 路径过滤 - 只允许公开接口 ===')

	config = OpenApiMcpConfig(
		path_patterns=['/api/public/*'],  # 只允许 /api/public/ 下的接口
		mask_sensitive_data=True,
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，配置路径过滤')
	print('✓ 只允许访问 /api/public/* 路径')
	print('✗ /api/admin/users 将被拒绝访问')
	print('✗ /api/auth/login 将被拒绝访问')


# 示例 3: 标签过滤 - 允许特定标签的接口
def example_tag_filter():
	"""示例 3: 使用标签过滤"""
	print('\n=== 示例 3: 标签过滤 - 只允许 public 标签 ===')

	config = OpenApiMcpConfig(
		allowed_tags=['public'],  # 只允许 public 标签的接口
		blocked_tags=['admin'],  # 明确禁止 admin 标签
		mask_sensitive_data=True,
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，配置标签过滤')
	print('✓ 只允许访问带有 "public" 标签的接口')
	print('✗ 带有 "admin" 标签的接口将被拒绝')


# 示例 4: 自定义过滤函数
def example_custom_filter():
	"""示例 4: 使用自定义过滤函数"""
	print('\n=== 示例 4: 自定义过滤函数 ===')

	def custom_filter(tool_name: str, kwargs: dict) -> bool:
		"""自定义过滤逻辑

		拒绝所有包含 'admin' 的路径，以及特定的工具
		"""
		# 拒绝 admin 路径
		if 'path' in kwargs and 'admin' in kwargs['path']:
			return False

		# 允许其他所有请求
		return True

	config = OpenApiMcpConfig(
		tool_filter=custom_filter,  # 使用自定义过滤函数
		mask_sensitive_data=True,
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，配置自定义过滤函数')
	print('✓ 自定义逻辑：拒绝包含 "admin" 的路径')


# 示例 5: 启用访问日志记录
def example_access_logging():
	"""示例 5: 启用访问日志记录"""
	print('\n=== 示例 5: 访问日志记录 ===')

	config = OpenApiMcpConfig(
		enable_access_logging=True,  # 启用访问日志
		mask_sensitive_data=True,  # 日志中的敏感数据也会被脱敏
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，启用访问日志记录')
	print('✓ 所有工具调用都会被记录到日志')
	print('✓ 日志中的敏感数据会被自动脱敏')


# 示例 6: 组合使用多种安全功能
def example_combined_security():
	"""示例 6: 组合使用多种安全功能"""
	print('\n=== 示例 6: 组合使用多种安全功能 ===')

	config = OpenApiMcpConfig(
		# 路径过滤
		path_patterns=['/api/public/*', '/api/auth/*'],
		# 标签过滤
		blocked_tags=['admin', 'internal'],
		# 敏感数据脱敏
		mask_sensitive_data=True,
		# 访问日志
		enable_access_logging=True,
		# CORS 配置
		allowed_origins=[
			'http://localhost:3000',
			'https://example.com',
		],
	)

	server = OpenApiMcpServer(app, config)
	print('✓ 创建 MCP Server，配置完整的安全策略')
	print('✓ 路径过滤: 只允许 /api/public/* 和 /api/auth/*')
	print('✓ 标签过滤: 禁止 admin 和 internal 标签')
	print('✓ 敏感数据脱敏: 自动脱敏密码、token 等')
	print('✓ 访问日志: 记录所有工具调用')
	print('✓ CORS: 只允许特定来源')


# 运行所有示例
if __name__ == '__main__':
	print('OpenAPI MCP Server - 安全功能示例')
	print('=' * 50)

	example_basic_masking()
	example_path_filter()
	example_tag_filter()
	example_custom_filter()
	example_access_logging()
	example_combined_security()

	print('\n' + '=' * 50)
	print('所有示例运行完成！')
	print('\n使用建议:')
	print('1. 生产环境建议启用敏感数据脱敏')
	print('2. 根据需要配置路径或标签过滤')
	print('3. 启用访问日志以便安全审计')
	print('4. 配置适当的 CORS 策略')
