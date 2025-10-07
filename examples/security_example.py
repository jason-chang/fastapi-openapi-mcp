"""
安全功能示例

展示 OpenAPI MCP Server 的各种安全功能，包括数据脱敏、访问控制、审计日志等。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.config import McpServerConfig
from openapi_mcp.security import AccessLogEntry, AuditLogger, SecurityFilter


# 创建包含敏感数据的示例应用
def create_sensitive_app() -> FastAPI:
	"""创建包含敏感数据的示例应用"""
	app = FastAPI(
		title='Security Demo API',
		version='1.0.0',
		description='演示安全功能的 API，包含各种敏感数据',
	)

	# 包含敏感信息的模型
	class UserProfile(BaseModel):
		id: int
		username: str
		email: str
		password: str = Field(..., description='用户密码')
		ssn: str = Field(..., description='社会安全号码')
		credit_card: str = Field(..., description='信用卡号')
		api_keys: list[str] = Field(default_factory=list, description='API密钥列表')

	class InternalConfig(BaseModel):
		db_password: str
		jwt_secret: str
		encryption_key: str
		internal_tokens: dict[str, str]

	# 公开接口（无敏感信息）
	@app.get('/public/status', tags=['public'])
	async def public_status():
		"""公开状态接口"""
		return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

	@app.get('/public/users/{user_id}/profile', tags=['public'])
	async def get_public_user_profile(user_id: int):
		"""获取公开用户信息"""
		return {
			'id': user_id,
			'username': f'user_{user_id}',
			'public_info': 'This is public information',
		}

	# 私有接口（包含敏感信息）
	@app.post('/private/users', tags=['private'])
	async def create_user(user: UserProfile):
		"""创建用户（包含敏感信息）"""
		# 模拟保存用户
		return {
			'id': user.id,
			'username': user.username,
			'email': user.email,
			'status': 'created',
			'password': user.password,  # 实际中不应该返回密码
			'ssn': user.ssn,
			'credit_card': user.credit_card,
			'api_keys': user.api_keys,
		}

	@app.get('/private/users/{user_id}/full', tags=['private'])
	async def get_full_user_profile(user_id: int):
		"""获取完整用户信息（包含敏感数据）"""
		return {
			'id': user_id,
			'username': f'user_{user_id}',
			'email': f'user_{user_id}@example.com',
			'password': 'super_secret_password_123',
			'ssn': '123-45-6789',
			'credit_card': '4532-1234-5678-9012',
			'api_keys': ['sk_live_1234567890abcdef', 'sk_test_abcdef1234567890'],
			'internal_notes': 'User has special privileges',
		}

	# 管理员接口（高度敏感）
	@app.get('/admin/config', tags=['admin'])
	async def get_admin_config():
		"""获取管理员配置（高度敏感）"""
		return {
			'database': {
				'host': 'db.example.com',
				'username': 'admin',
				'password': 'admin_secret_password',
				'name': 'production_db',
			},
			'jwt': {'secret': 'jwt_super_secret_key_12345', 'expiration': 3600},
			'encryption': {
				'key': 'encryption_key_32_bytes_long',
				'algorithm': 'AES-256-GCM',
			},
			'api_keys': {
				'payment_gateway': 'pg_sk_1234567890abcdef',
				'email_service': 'email_sk_abcdef1234567890',
			},
		}

	@app.delete('/admin/users/{user_id}', tags=['admin'])
	async def delete_user(user_id: int, reason: str = ''):
		"""删除用户（危险操作）"""
		return {
			'user_id': user_id,
			'deleted': True,
			'reason': reason,
			'timestamp': datetime.now().isoformat(),
			'performed_by': 'admin_user',
		}

	return app


# 自定义安全过滤器
class CustomSecurityFilter(SecurityFilter):
	"""自定义安全过滤器，演示各种脱敏规则"""

	def __init__(self):
		super().__init__()
		# 定义敏感字段模式
		self.sensitive_patterns = {
			'password': r'.*',
			'ssn': r'\d{3}-\d{2}-\d{4}',
			'credit_card': r'\d{4}-\d{4}-\d{4}-\d{4}',
			'api_key': r'sk_[a-zA-Z0-9]+',
			'secret': r'.*',
			'token': r'.*',
		}

	def filter_tool(self, tool_name: str, tool_info: dict) -> bool:
		"""工具过滤规则"""
		# 禁用危险操作工具
		dangerous_tools = ['delete_endpoint', 'modify_server_config']
		if tool_name in dangerous_tools:
			return False

		# 限制管理员工具的使用
		if tool_name.startswith('admin_'):
			return False  # 需要特殊权限

		return True

	def filter_data(self, data: Any, context: str = '') -> Any:
		"""数据脱敏处理"""
		if isinstance(data, dict):
			return self._filter_dict(data)
		elif isinstance(data, list):
			return [self.filter_data(item, context) for item in data]
		elif isinstance(data, str):
			return self._filter_string(data)
		return data

	def _filter_dict(self, data: dict) -> dict:
		"""过滤字典数据"""
		filtered = {}

		for key, value in data.items():
			key_lower = key.lower()

			# 检查是否为敏感字段
			if any(
				pattern in key_lower
				for pattern in [
					'password',
					'passwd',
					'pwd',
					'ssn',
					'social_security',
					'credit_card',
					'card_number',
					'api_key',
					'apikey',
					'secret',
					'token',
					'encryption_key',
					'jwt_secret',
				]
			):
				# 应用不同的脱敏策略
				if 'password' in key_lower:
					filtered[key] = '***'
				elif 'ssn' in key_lower:
					filtered[key] = '***-**-****'
				elif 'credit_card' in key_lower:
					filtered[key] = '****-****-****-****'
				elif 'api_key' in key_lower:
					if isinstance(value, str) and len(value) > 8:
						filtered[key] = f'{value[:4]}...{value[-4:]}'
					else:
						filtered[key] = '***'
				else:
					filtered[key] = '[REDACTED]'
			else:
				# 递归处理嵌套结构
				filtered[key] = self.filter_data(value, f'dict.{key}')

		return filtered

	def _filter_string(self, value: str) -> str:
		"""过滤字符串数据"""
		# 检查是否包含敏感信息模式
		import re

		# 信用卡号模式
		if re.match(r'\d{4}-\d{4}-\d{4}-\d{4}', value):
			return '****-****-****-****'

		# SSN 模式
		if re.match(r'\d{3}-\d{2}-\d{4}', value):
			return '***-**-****'

		# API Key 模式
		if re.match(r'sk_[a-zA-Z0-9]+', value):
			if len(value) > 8:
				return f'{value[:4]}...{value[-4:]}'
			return '***'

		return value


# 自定义审计日志器
class CustomAuditLogger(AuditLogger):
	"""自定义审计日志器"""

	def __init__(self):
		super().__init__()
		self.audit_log = []
		# 配置日志
		logging.basicConfig(level=logging.INFO)
		self.logger = logging.getLogger('security_audit')

	def log_access(self, entry: AccessLogEntry):
		"""记录访问日志"""
		super().log_access(entry)

		# 自定义日志格式
		log_message = (
			f'[ACCESS] {entry.timestamp} - '
			f'Tool: {entry.tool_name} - '
			f'User: {entry.user_id} - '
			f'IP: {entry.client_ip} - '
			f'Success: {entry.success}'
		)

		self.logger.info(log_message)

		# 检查可疑活动
		self._check_suspicious_activity(entry)

	def log_sensitive_operation(self, operation: str, user_id: str, details: dict):
		"""记录敏感操作"""
		timestamp = datetime.now().isoformat()

		audit_entry = {
			'timestamp': timestamp,
			'operation': operation,
			'user_id': user_id,
			'details': details,
			'level': 'HIGH',
		}

		self.audit_log.append(audit_entry)

		# 高优先级日志
		log_message = f'[SECURITY] {timestamp} - {operation} by {user_id}'
		self.logger.warning(log_message)

	def _check_suspicious_activity(self, entry: AccessLogEntry):
		"""检查可疑活动"""
		# 检查频繁访问
		recent_entries = [
			e
			for e in self.audit_log[-10:]  # 最近10条记录
			if e.get('user_id') == entry.user_id
			and e.get('timestamp', '')
			> entry.timestamp.replace(second=entry.timestamp.second - 60)
		]

		if len(recent_entries) > 5:  # 1分钟内超过5次操作
			self.logger.warning(
				f'[SUSPICIOUS] High frequency access detected for user {entry.user_id}'
			)


# 演示1: 基础数据脱敏
def demo_basic_data_sanitization():
	"""演示基础数据脱敏功能"""
	print('=== 演示1: 基础数据脱敏 ===')

	app = create_sensitive_app()

	# 使用默认安全过滤器
	config = McpServerConfig(
		security_filter=SecurityFilter(),
		access_log_enabled=True,
		audit_sensitive_operations=True,
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-basic-security')

	print('✅ 基础安全配置已应用')
	print('   - 默认数据脱敏规则已启用')
	print('   - 访问日志已启用')
	print('   - 敏感操作审计已启用')

	return mcp_server


# 演示2: 自定义安全过滤
def demo_custom_security_filtering():
	"""演示自定义安全过滤"""
	print('\n=== 演示2: 自定义安全过滤 ===')

	app = create_sensitive_app()

	# 使用自定义安全过滤器
	custom_filter = CustomSecurityFilter()
	config = McpServerConfig(security_filter=custom_filter, access_log_enabled=True)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-custom-security')

	print('✅ 自定义安全配置已应用')
	print('   - 自定义脱敏规则已启用')
	print('   - 危险工具已被禁用')
	print('   - 管理员工具需要特殊权限')

	return mcp_server


# 演示3: 高级审计功能
def demo_advanced_audit():
	"""演示高级审计功能"""
	print('\n=== 演示3: 高级审计功能 ===')

	app = create_sensitive_app()

	# 使用自定义审计日志器
	audit_logger = CustomAuditLogger()
	config = McpServerConfig(
		security_filter=CustomSecurityFilter(),
		access_log_enabled=True,
		audit_logger=audit_logger,
		detailed_audit_logging=True,
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-audit')

	print('✅ 高级审计配置已应用')
	print('   - 自定义审计日志器已启用')
	print('   - 可疑活动检测已启用')
	print('   - 详细审计日志已启用')

	return mcp_server, audit_logger


# 演示4: 多层安全控制
def demo_multi_layer_security():
	"""演示多层安全控制"""
	print('\n=== 演示4: 多层安全控制 ===')

	app = create_sensitive_app()

	# 创建多层安全配置
	class MultiLayerSecurityFilter(SecurityFilter):
		def __init__(self):
			super().__init__()
			self.access_count = {}
			self.blocked_ips = set()

		def filter_request(self, client_ip: str, user_id: str, tool_name: str) -> bool:
			"""请求级别的过滤"""
			# IP 黑名单检查
			if client_ip in self.blocked_ips:
				return False

			# 频率限制
			key = f'{client_ip}:{user_id}'
			self.access_count[key] = self.access_count.get(key, 0) + 1

			if self.access_count[key] > 100:  # 每个用户/IP组合最多100次请求
				self.blocked_ips.add(client_ip)
				return False

			return True

		def filter_data(self, data: Any, context: str = '') -> Any:
			"""数据过滤 - 应用多层脱敏"""
			# 第一层：基础脱敏
			filtered = super().filter_data(data, context)

			# 第二层：上下文感知脱敏
			if 'admin' not in context.lower():
				# 非管理员上下文，进一步脱敏
				if isinstance(filtered, dict):
					filtered = self._apply_contextual_filtering(filtered)

			return filtered

		def _apply_contextual_filtering(self, data: dict) -> dict:
			"""应用上下文相关的过滤"""
			filtered = data.copy()

			# 在非管理员上下文中隐藏更多字段
			high_sensitivity_fields = ['internal_notes', 'performed_by', 'reason']

			for field in high_sensitivity_fields:
				if field in filtered:
					filtered[field] = '[HIDDEN]'

			return filtered

	config = McpServerConfig(
		security_filter=MultiLayerSecurityFilter(),
		access_log_enabled=True,
		rate_limiting_enabled=True,
		max_requests_per_minute=60,
	)

	mcp_server = OpenApiMcpServer(app, config=config)
	mcp_server.mount('/mcp-multi-layer')

	print('✅ 多层安全控制已应用')
	print('   - IP 黑名单检查已启用')
	print('   - 频率限制已启用')
	print('   - 上下文感知脱敏已启用')
	print('   - 速率限制已启用')

	return mcp_server


# 安全测试函数
async def test_security_features():
	"""测试安全功能"""
	print('\n=== 安全功能测试 ===')

	# 这里可以添加实际的安全测试代码
	# 比如模拟访问敏感接口，验证脱敏效果等

	test_cases = [
		{
			'name': '测试用户密码脱敏',
			'data': {'username': 'test', 'password': 'secret123'},
			'expected': {'username': 'test', 'password': '***'},
		},
		{
			'name': '测试信用卡号脱敏',
			'data': {'card_number': '4532-1234-5678-9012'},
			'expected': {'card_number': '****-****-****-****'},
		},
		{
			'name': '测试API密钥脱敏',
			'data': {'api_key': 'sk_live_1234567890abcdef'},
			'expected': {'api_key': 'sk_l...cdef'},
		},
	]

	security_filter = CustomSecurityFilter()

	for test_case in test_cases:
		print(f'\n  测试: {test_case["name"]}')
		result = security_filter.filter_data(test_case['data'])
		expected = test_case['expected']

		if result == expected:
			print(f'    ✅ 通过: {result}')
		else:
			print(f'    ❌ 失败: 期望 {expected}, 得到 {result}')


def main():
	"""运行所有安全演示"""
	print('🔒 OpenAPI MCP 安全功能演示')
	print('=' * 60)

	# 创建各种安全配置
	servers = []

	try:
		# 基础数据脱敏
		server1 = demo_basic_data_sanitization()
		servers.append(('基础安全', server1))

		# 自定义安全过滤
		server2 = demo_custom_security_filtering()
		servers.append(('自定义安全', server2))

		# 高级审计功能
		server3, audit_logger = demo_advanced_audit()
		servers.append(('高级审计', server3))

		# 多层安全控制
		server4 = demo_multi_layer_security()
		servers.append(('多层安全', server4))

	except Exception as e:
		print(f'❌ 配置创建失败: {e}')
		return

	print(f'\n✅ 成功创建 {len(servers)} 个安全配置示例')

	# 安全功能总结
	print('\n🛡️ 安全功能总结:')
	print('   1. 基础安全 - 默认数据脱敏和访问日志')
	print('   2. 自定义安全 - 自定义脱敏规则和工具过滤')
	print('   3. 高级审计 - 详细审计日志和可疑活动检测')
	print('   4. 多层安全 - IP黑名单、频率限制、上下文感知')

	# 运行安全测试
	print('\n🧪 运行安全功能测试...')
	asyncio.run(test_security_features())

	print('\n💡 安全建议:')
	print('   - 生产环境必须启用安全过滤')
	print('   - 定期审查审计日志')
	print('   - 实施适当的访问控制策略')
	print('   - 监控可疑活动模式')
	print('   - 定期更新安全规则')


if __name__ == '__main__':
	main()
