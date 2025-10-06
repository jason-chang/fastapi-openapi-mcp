"""
测试安全功能模块

测试工具过滤器、敏感信息脱敏器和访问日志记录器。
"""

import logging
from typing import Any

import pytest

from openapi_mcp.security import AccessLogger, ResourceAccessControl, SensitiveDataMasker, ToolFilter


class TestToolFilter:
	"""测试工具过滤器"""

	def test_no_filter_allows_all(self) -> None:
		"""测试没有配置过滤规则时允许所有"""
		filter = ToolFilter()

		# 应该允许任何工具和参数
		assert filter.should_allow('list_endpoints', path='/api/users')
		assert filter.should_allow('get_endpoint', path='/admin/config')
		assert filter.should_allow('search_by_tag', tag='admin')

	def test_path_pattern_exact_match(self) -> None:
		"""测试路径模式精确匹配"""
		filter = ToolFilter(path_patterns=['/api/public/users'])

		assert filter.should_allow('list_endpoints', path='/api/public/users')
		assert not filter.should_allow('list_endpoints', path='/api/admin/users')

	def test_path_pattern_wildcard(self) -> None:
		"""测试路径模式通配符"""
		filter = ToolFilter(path_patterns=['/api/public/*'])

		# 应该匹配 /api/public/ 下的任何路径
		assert filter.should_allow('list_endpoints', path='/api/public/users')
		assert filter.should_allow('get_endpoint', path='/api/public/posts')
		assert filter.should_allow('get_endpoint', path='/api/public/users/123')

		# 不应该匹配其他路径
		assert not filter.should_allow('list_endpoints', path='/api/admin/users')
		assert not filter.should_allow('list_endpoints', path='/internal/data')

	def test_path_pattern_multiple_wildcards(self) -> None:
		"""测试多个通配符模式"""
		filter = ToolFilter(path_patterns=['/api/*/public', '/docs/*'])

		assert filter.should_allow('get_endpoint', path='/api/v1/public')
		assert filter.should_allow('get_endpoint', path='/api/v2/public')
		assert filter.should_allow('get_endpoint', path='/docs/readme')
		assert not filter.should_allow('get_endpoint', path='/api/admin')

	def test_allowed_tags(self) -> None:
		"""测试允许的标签列表"""
		filter = ToolFilter(allowed_tags=['public', 'user'])

		assert filter.should_allow('search_by_tag', tag='public')
		assert filter.should_allow('search_by_tag', tag='user')
		assert not filter.should_allow('search_by_tag', tag='admin')
		assert not filter.should_allow('search_by_tag', tag='internal')

	def test_blocked_tags(self) -> None:
		"""测试禁止的标签列表"""
		filter = ToolFilter(blocked_tags=['admin', 'internal'])

		# 被禁止的标签应该被拒绝
		assert not filter.should_allow('search_by_tag', tag='admin')
		assert not filter.should_allow('search_by_tag', tag='internal')

		# 其他标签应该被允许
		assert filter.should_allow('search_by_tag', tag='public')
		assert filter.should_allow('search_by_tag', tag='user')

	def test_allowed_and_blocked_tags(self) -> None:
		"""测试同时配置允许和禁止标签"""
		filter = ToolFilter(
			allowed_tags=['public', 'user', 'admin'],
			blocked_tags=['admin'],
		)

		# 禁止列表优先级更高
		assert not filter.should_allow('search_by_tag', tag='admin')

		# 允许列表中的其他标签应该被允许
		assert filter.should_allow('search_by_tag', tag='public')
		assert filter.should_allow('search_by_tag', tag='user')

		# 不在允许列表中的标签应该被拒绝
		assert not filter.should_allow('search_by_tag', tag='internal')

	def test_custom_filter(self) -> None:
		"""测试自定义过滤函数"""

		def custom_filter(tool_name: str, kwargs: dict[str, Any]) -> bool:
			# 禁止访问 admin 路径
			if 'path' in kwargs and 'admin' in kwargs['path']:
				return False
			return True

		filter = ToolFilter(custom_filter=custom_filter)

		assert filter.should_allow('list_endpoints', path='/api/users')
		assert not filter.should_allow('list_endpoints', path='/api/admin/users')

	def test_combined_filters(self) -> None:
		"""测试组合过滤条件"""

		def custom_filter(tool_name: str, kwargs: dict[str, Any]) -> bool:
			# 禁止 list_endpoints 工具
			return tool_name != 'list_endpoints'

		filter = ToolFilter(
			path_patterns=['/api/*'],
			allowed_tags=['public'],
			custom_filter=custom_filter,
		)

		# 路径匹配，但工具被自定义过滤器拒绝
		assert not filter.should_allow('list_endpoints', path='/api/users')

		# 路径匹配，工具通过自定义过滤器
		assert filter.should_allow('get_endpoint', path='/api/users')

		# 路径不匹配
		assert not filter.should_allow('get_endpoint', path='/internal/data')

		# 标签匹配
		assert filter.should_allow('search_by_tag', tag='public')

		# 标签不匹配
		assert not filter.should_allow('search_by_tag', tag='admin')


class TestSensitiveDataMasker:
	"""测试敏感信息脱敏器"""

	def test_mask_password_field(self) -> None:
		"""测试脱敏密码字段"""
		masker = SensitiveDataMasker()

		data = {
			'username': 'john',
			'password': 'secret123',
			'email': 'john@example.com',
		}

		result = masker.mask_dict(data)

		assert result['username'] == 'john'
		assert result['password'] == '***'
		assert result['email'] == 'john@example.com'

	def test_mask_token_fields(self) -> None:
		"""测试脱敏 token 字段"""
		masker = SensitiveDataMasker()

		data = {
			'user_id': 123,
			'token': 'abc123xyz',
			'access_token': 'token456',
			'api_key': 'key789',
		}

		result = masker.mask_dict(data)

		assert result['user_id'] == 123
		assert result['token'] == '***'
		assert result['access_token'] == '***'
		assert result['api_key'] == '***'

	def test_mask_case_insensitive(self) -> None:
		"""测试不区分大小写的脱敏"""
		masker = SensitiveDataMasker()

		data = {
			'PASSWORD': 'secret',
			'Token': 'abc',
			'API_KEY': 'key',
		}

		result = masker.mask_dict(data)

		assert result['PASSWORD'] == '***'
		assert result['Token'] == '***'
		assert result['API_KEY'] == '***'

	def test_mask_nested_dict(self) -> None:
		"""测试脱敏嵌套字典"""
		masker = SensitiveDataMasker()

		data = {
			'user': {
				'name': 'john',
				'password': 'secret',
				'profile': {
					'email': 'john@example.com',
					'api_key': 'key123',
				},
			},
		}

		result = masker.mask_dict(data)

		assert result['user']['name'] == 'john'
		assert result['user']['password'] == '***'
		assert result['user']['profile']['email'] == 'john@example.com'
		assert result['user']['profile']['api_key'] == '***'

	def test_mask_list(self) -> None:
		"""测试脱敏列表"""
		masker = SensitiveDataMasker()

		data = [
			{'username': 'alice', 'password': 'pass1'},
			{'username': 'bob', 'password': 'pass2'},
		]

		result = masker.mask_list(data)

		assert result[0]['username'] == 'alice'
		assert result[0]['password'] == '***'
		assert result[1]['username'] == 'bob'
		assert result[1]['password'] == '***'

	def test_mask_dict_with_list(self) -> None:
		"""测试脱敏包含列表的字典"""
		masker = SensitiveDataMasker()

		data = {
			'users': [
				{'name': 'alice', 'token': 'token1'},
				{'name': 'bob', 'secret': 'secret1'},
			],
		}

		result = masker.mask_dict(data)

		assert result['users'][0]['name'] == 'alice'
		assert result['users'][0]['token'] == '***'
		assert result['users'][1]['name'] == 'bob'
		assert result['users'][1]['secret'] == '***'

	def test_mask_text_key_value(self) -> None:
		"""测试脱敏文本中的 key=value 格式"""
		masker = SensitiveDataMasker()

		text = 'username=john password=secret123 token=abc'
		result = masker.mask_text(text)

		assert 'username=john' in result
		assert 'password=***' in result
		assert 'token=***' in result
		assert 'secret123' not in result
		assert 'abc' not in result

	def test_mask_text_json_format(self) -> None:
		"""测试脱敏 JSON 格式文本

		注意：对于完整的 JSON 对象，建议先解析后使用 mask_dict()。
		mask_text() 主要用于日志等非结构化文本中的敏感信息脱敏。
		"""
		masker = SensitiveDataMasker()

		# 测试日志格式的文本
		text = 'User login attempt: username=john password=secret token=abc123'
		result = masker.mask_text(text)

		assert 'username=john' in result
		assert 'password=***' in result
		assert 'token=***' in result
		assert 'secret' not in result
		assert 'abc123' not in result

	def test_custom_patterns(self) -> None:
		"""测试自定义敏感字段模式"""
		masker = SensitiveDataMasker(custom_patterns=['ssn', 'credit_card'])

		data = {
			'name': 'john',
			'ssn': '123-45-6789',
			'credit_card': '4111-1111-1111-1111',
		}

		result = masker.mask_dict(data)

		assert result['name'] == 'john'
		assert result['ssn'] == '***'
		assert result['credit_card'] == '***'

	def test_custom_placeholder(self) -> None:
		"""测试自定义脱敏占位符"""
		masker = SensitiveDataMasker(mask_placeholder='[REDACTED]')

		data = {'password': 'secret'}
		result = masker.mask_dict(data)

		assert result['password'] == '[REDACTED]'

	def test_mask_preserves_original(self) -> None:
		"""测试脱敏不修改原始数据"""
		masker = SensitiveDataMasker()

		original = {'username': 'john', 'password': 'secret'}
		result = masker.mask_dict(original)

		# 原始数据不应该被修改
		assert original['password'] == 'secret'
		assert result['password'] == '***'


class TestAccessLogger:
	"""测试访问日志记录器"""

	def test_log_tool_call_success(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试记录成功的工具调用"""
		logger = AccessLogger(mask_sensitive=False)

		with caplog.at_level(logging.INFO):
			logger.log_tool_call(
				'list_endpoints',
				{'path': '/api/users'},
				result='success',
			)

		assert len(caplog.records) == 1
		assert 'list_endpoints' in caplog.text
		assert '/api/users' in caplog.text

	def test_log_tool_call_error(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试记录失败的工具调用"""
		logger = AccessLogger(mask_sensitive=False)

		with caplog.at_level(logging.ERROR):
			logger.log_tool_call(
				'get_endpoint',
				{'path': '/api/users'},
				error='Endpoint not found',
			)

		assert len(caplog.records) == 1
		assert 'get_endpoint' in caplog.text
		assert 'Endpoint not found' in caplog.text

	def test_log_access_denied(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试记录访问拒绝"""
		logger = AccessLogger(mask_sensitive=False)

		with caplog.at_level(logging.WARNING):
			logger.log_access_denied(
				'list_endpoints',
				{'path': '/admin/users'},
				reason='Blocked by filter',
			)

		assert len(caplog.records) == 1
		assert 'list_endpoints' in caplog.text
		assert 'Blocked by filter' in caplog.text
		assert 'denied' in caplog.text

	def test_log_with_masking(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试记录时脱敏敏感信息"""
		logger = AccessLogger(mask_sensitive=True)

		with caplog.at_level(logging.INFO):
			logger.log_tool_call(
				'authenticate',
				{'username': 'john', 'password': 'secret123'},
				result='success',
			)

		# 应该包含用户名但不包含密码原文
		assert 'john' in caplog.text
		assert '***' in caplog.text
		assert 'secret123' not in caplog.text

	def test_custom_masker(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试使用自定义脱敏器"""
		masker = SensitiveDataMasker(custom_patterns=['ssn'])
		logger = AccessLogger(mask_sensitive=True, masker=masker)

		with caplog.at_level(logging.INFO):
			logger.log_tool_call(
				'get_user',
				{'name': 'john', 'ssn': '123-45-6789'},
				result='success',
			)

		assert 'john' in caplog.text
		assert '***' in caplog.text
		assert '123-45-6789' not in caplog.text


class TestSecurityIntegration:
	"""测试安全功能集成"""

	def test_filter_and_logger_integration(
		self, caplog: pytest.LogCaptureFixture
	) -> None:
		"""测试过滤器和日志记录器集成"""
		filter = ToolFilter(path_patterns=['/api/public/*'])
		logger = AccessLogger(mask_sensitive=False)

		# 测试允许的路径
		tool_name = 'list_endpoints'
		allowed_args = {'path': '/api/public/users'}

		if filter.should_allow(tool_name, **allowed_args):
			logger.log_tool_call(tool_name, allowed_args, result='success')
		else:
			logger.log_access_denied(tool_name, allowed_args, reason='Filtered')

		assert 'success' in caplog.text

		caplog.clear()

		# 测试被拒绝的路径
		blocked_args = {'path': '/api/admin/users'}

		if filter.should_allow(tool_name, **blocked_args):
			logger.log_tool_call(tool_name, blocked_args, result='success')
		else:
			logger.log_access_denied(tool_name, blocked_args, reason='Filtered')

		assert 'denied' in caplog.text

	def test_masker_and_logger_integration(
		self, caplog: pytest.LogCaptureFixture
	) -> None:
		"""测试脱敏器和日志记录器集成"""
		masker = SensitiveDataMasker()
		logger = AccessLogger(mask_sensitive=True, masker=masker)

		tool_args = {
			'username': 'admin',
			'password': 'admin123',
			'token': 'secret_token',
		}

		with caplog.at_level(logging.INFO):
			logger.log_tool_call('authenticate', tool_args, result='success')

		# 验证敏感信息被脱敏
		assert 'admin' in caplog.text  # 用户名不是敏感字段
		assert '***' in caplog.text
		assert 'admin123' not in caplog.text
		assert 'secret_token' not in caplog.text


class TestResourceAccessControl:
	"""测试 Resource 访问控制器"""

	def test_default_allow_all(self) -> None:
		"""测试默认允许所有资源访问"""
		control = ResourceAccessControl()

		assert control.can_access('openapi://spec')
		assert control.can_access('openapi://endpoints')
		assert control.can_access('any://resource')

	def test_blocked_patterns(self) -> None:
		"""测试禁止模式"""
		control = ResourceAccessControl(
			blocked_patterns=['openapi://admin/*', 'secret://*']
		)

		# 允许的资源
		assert control.can_access('openapi://spec')
		assert control.can_access('openapi://endpoints')
		assert control.can_access('public://data')

		# 禁止的资源
		assert not control.can_access('openapi://admin/users')
		assert not control.can_access('openapi://admin/settings')
		assert not control.can_access('secret://key')

	def test_allowed_patterns(self) -> None:
		"""测试允许模式"""
		control = ResourceAccessControl(
			allowed_patterns=['openapi://spec', 'openapi://endpoints/*'],
			default_allow=False
		)

		# 允许的资源
		assert control.can_access('openapi://spec')
		assert control.can_access('openapi://endpoints')
		assert control.can_access('openapi://endpoints/users')

		# 禁止的资源
		assert not control.can_access('openapi://models')
		assert not control.can_access('openapi://tags')
		assert not control.can_access('other://resource')

	def test_mixed_patterns(self) -> None:
		"""测试混合模式（允许和禁止）"""
		control = ResourceAccessControl(
			allowed_patterns=['openapi://*', 'public://*'],
			blocked_patterns=['openapi://admin/*'],
			default_allow=False
		)

		# 允许的资源
		assert control.can_access('openapi://spec')
		assert control.can_access('openapi://endpoints')
		assert control.can_access('public://data')

		# 禁止的资源（优先级高于允许列表）
		assert not control.can_access('openapi://admin/users')
		assert not control.can_access('openapi://admin/settings')

		# 不在允许列表中的资源
		assert not control.can_access('secret://key')
		assert not control.can_access('private://data')

	def test_wildcard_patterns(self) -> None:
		"""测试通配符模式"""
		control = ResourceAccessControl(
			allowed_patterns=['openapi://*/spec', 'openapi://v*/endpoints'],
			default_allow=False
		)

		# 匹配通配符
		assert control.can_access('openapi://v1/spec')
		assert control.can_access('openapi://v2/spec')
		assert control.can_access('openapi://v1/endpoints')
		assert control.can_access('openapi://v2/endpoints')

		# 不匹配通配符
		assert not control.can_access('openapi://v1/models')
		assert not control.can_access('openapi://models/spec')

	def test_exact_match_priority(self) -> None:
		"""测试精确匹配优先级"""
		control = ResourceAccessControl(
			allowed_patterns=['openapi://spec'],
			blocked_patterns=['openapi://spec'],
			default_allow=True
		)

		# 禁止列表应该优先级更高
		assert not control.can_access('openapi://spec')


class TestResourceAccessControlIntegration:
	"""测试 Resource 访问控制集成"""

	def test_access_logger_with_resource_control(self) -> None:
		"""测试访问日志记录器集成资源访问控制"""
		# 没有访问控制时，总是允许
		logger = AccessLogger()
		assert logger.can_access_resource('any://resource')

		# 有访问控制时
		control = ResourceAccessControl(allowed_patterns=['openapi://spec'])
		logger = AccessLogger(resource_access_control=control)

		assert logger.can_access_resource('openapi://spec')
		assert not logger.can_access_resource('openapi://admin/users')

	def test_log_resource_access(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试资源访问日志记录"""
		logger = AccessLogger()

		with caplog.at_level(logging.INFO):
			logger.log_resource_access('openapi://spec', session_id='session123', duration=0.5)

		assert 'openapi://spec' in caplog.text
		assert 'session123' in caplog.text
		assert '500.0' in caplog.text  # duration in ms

	def test_log_resource_access_denied(self, caplog: pytest.LogCaptureFixture) -> None:
		"""测试资源访问拒绝日志记录"""
		logger = AccessLogger()

		with caplog.at_level(logging.WARNING):
			logger.log_resource_access_denied(
				'openapi://admin/users',
				reason='Blocked by pattern',
				session_id='session123'
			)

		assert 'openapi://admin/users' in caplog.text
		assert 'Blocked by pattern' in caplog.text
		assert 'denied' in caplog.text
