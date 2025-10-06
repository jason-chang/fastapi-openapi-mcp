"""
安全功能模块

提供工具过滤、敏感信息脱敏、访问日志记录等安全功能。
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

# 配置日志记录器
logger = logging.getLogger(__name__)


class ToolFilter:
	"""工具过滤器

	根据配置规则过滤可用的工具，支持基于路径、标签和自定义函数的过滤。

	Example:
		>>> # 基于路径过滤
		>>> filter = ToolFilter(path_patterns=['/api/public/*'])
		>>> allowed = filter.should_allow('list_endpoints', '/api/public/users')
		>>>
		>>> # 基于标签过滤
		>>> filter = ToolFilter(allowed_tags=['public', 'user'])
		>>> allowed = filter.should_allow('search_by_tag', tag='public')
		>>>
		>>> # 自定义过滤函数
		>>> def custom_filter(tool_name: str, **kwargs: Any) -> bool:
		...     return 'admin' not in kwargs.get('path', '')
		>>> filter = ToolFilter(custom_filter=custom_filter)
	"""

	def __init__(
		self,
		path_patterns: list[str] | None = None,
		allowed_tags: list[str] | None = None,
		blocked_tags: list[str] | None = None,
		custom_filter: Callable[[str, dict[str, Any]], bool] | None = None,
	) -> None:
		"""初始化工具过滤器

		Args:
			path_patterns: 允许的路径模式列表，支持通配符 *
			allowed_tags: 允许的标签列表，为空表示允许所有
			blocked_tags: 禁止的标签列表
			custom_filter: 自定义过滤函数，接收工具名和参数，返回是否允许
		"""
		self.path_patterns = path_patterns or []
		self.allowed_tags = allowed_tags or []
		self.blocked_tags = blocked_tags or []
		self.custom_filter = custom_filter

		# 将通配符模式转换为正则表达式
		self._path_regexes = [
			re.compile(self._pattern_to_regex(pattern))
			for pattern in self.path_patterns
		]

	def _pattern_to_regex(self, pattern: str) -> str:
		"""将通配符模式转换为正则表达式

		Args:
			pattern: 通配符模式，如 '/api/*/users'

		Returns:
			正则表达式字符串
		"""
		# 转义正则表达式特殊字符（除了 *）
		escaped = re.escape(pattern)
		# 将 \* 替换为正则表达式的 .*
		regex = escaped.replace(r'\*', '.*')
		return f'^{regex}$'

	def _check_path(self, path: str) -> bool:
		"""检查路径是否匹配允许的模式

		Args:
			path: 要检查的路径

		Returns:
			True 表示路径被允许
		"""
		if not self.path_patterns:
			# 没有配置路径模式，允许所有
			return True

		# 检查是否匹配任一模式
		for regex in self._path_regexes:
			if regex.match(path):
				return True

		return False

	def _check_tag(self, tag: str) -> bool:
		"""检查标签是否被允许

		Args:
			tag: 要检查的标签

		Returns:
			True 表示标签被允许
		"""
		# 先检查是否在禁止列表中
		if self.blocked_tags and tag in self.blocked_tags:
			return False

		# 如果有允许列表，检查是否在列表中
		if self.allowed_tags:
			return tag in self.allowed_tags

		# 没有允许列表，默认允许
		return True

	def should_allow(self, tool_name: str, **kwargs: Any) -> bool:
		"""判断是否允许执行工具

		Args:
			tool_name: 工具名称
			**kwargs: 工具参数，可能包含 path、tag 等

		Returns:
			True 表示允许执行，False 表示拒绝
		"""
		# 检查路径过滤
		if 'path' in kwargs:
			if not self._check_path(kwargs['path']):
				logger.info(
					f'Tool {tool_name} blocked by path filter: {kwargs["path"]}'
				)
				return False

		# 检查标签过滤
		if 'tag' in kwargs:
			if not self._check_tag(kwargs['tag']):
				logger.info(f'Tool {tool_name} blocked by tag filter: {kwargs["tag"]}')
				return False

		# 检查自定义过滤函数
		if self.custom_filter:
			if not self.custom_filter(tool_name, kwargs):
				logger.info(f'Tool {tool_name} blocked by custom filter')
				return False

		return True


class SensitiveDataMasker:
	"""敏感信息脱敏器

	对 API 响应中的敏感信息进行脱敏处理，防止泄露密码、token 等敏感数据。

	支持的脱敏类型：
	- 密码字段（password、passwd、pwd 等）
	- Token 字段（token、access_token、api_key 等）
	- 自定义敏感字段

	Example:
		>>> masker = SensitiveDataMasker()
		>>> data = {'username': 'john', 'password': 'secret123'}
		>>> masked = masker.mask_dict(data)
		>>> # {'username': 'john', 'password': '***'}
		>>>
		>>> # 添加自定义敏感字段
		>>> masker = SensitiveDataMasker(custom_patterns=['ssn', 'credit_card'])
	"""

	# 默认的敏感字段模式（不区分大小写）
	DEFAULT_SENSITIVE_PATTERNS = [
		'password',
		'passwd',
		'pwd',
		'token',
		'access_token',
		'refresh_token',
		'api_key',
		'apikey',
		'secret',
		'auth',
		'authorization',
		'credential',
	]

	# 脱敏占位符
	MASK_PLACEHOLDER = '***'

	def __init__(
		self,
		custom_patterns: list[str] | None = None,
		mask_placeholder: str | None = None,
	) -> None:
		"""初始化敏感信息脱敏器

		Args:
			custom_patterns: 自定义敏感字段模式列表
			mask_placeholder: 自定义脱敏占位符，默认为 '***'
		"""
		self.sensitive_patterns = self.DEFAULT_SENSITIVE_PATTERNS.copy()
		if custom_patterns:
			self.sensitive_patterns.extend(custom_patterns)

		self.mask_placeholder = mask_placeholder or self.MASK_PLACEHOLDER

		# 编译正则表达式（不区分大小写）
		self._sensitive_regexes = [
			re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns
		]

	def _is_sensitive_field(self, field_name: str) -> bool:
		"""判断字段名是否为敏感字段

		Args:
			field_name: 字段名

		Returns:
			True 表示是敏感字段
		"""
		for regex in self._sensitive_regexes:
			if regex.search(field_name):
				return True
		return False

	def mask_value(self, value: Any) -> Any:
		"""脱敏单个值

		Args:
			value: 要脱敏的值

		Returns:
			脱敏后的值
		"""
		if isinstance(value, str):
			return self.mask_placeholder
		elif isinstance(value, dict):
			return self.mask_dict(value)
		elif isinstance(value, list):
			return self.mask_list(value)
		else:
			# 其他类型（数字、布尔等）也脱敏
			return self.mask_placeholder

	def mask_dict(self, data: dict[str, Any]) -> dict[str, Any]:
		"""脱敏字典中的敏感字段

		递归处理嵌套字典和列表。

		Args:
			data: 要脱敏的字典

		Returns:
			脱敏后的字典（新字典，不修改原始数据）
		"""
		result: dict[str, Any] = {}

		for key, value in data.items():
			if self._is_sensitive_field(key):
				# 敏感字段，脱敏处理
				result[key] = self.mask_placeholder
			elif isinstance(value, dict):
				# 递归处理嵌套字典
				result[key] = self.mask_dict(value)
			elif isinstance(value, list):
				# 递归处理列表
				result[key] = self.mask_list(value)
			else:
				# 普通字段，保持原值
				result[key] = value

		return result

	def mask_list(self, data: list[Any]) -> list[Any]:
		"""脱敏列表中的敏感数据

		递归处理列表中的字典和嵌套列表。

		Args:
			data: 要脱敏的列表

		Returns:
			脱敏后的列表（新列表，不修改原始数据）
		"""
		result: list[Any] = []

		for item in data:
			if isinstance(item, dict):
				# 递归处理字典
				result.append(self.mask_dict(item))
			elif isinstance(item, list):
				# 递归处理嵌套列表
				result.append(self.mask_list(item))
			else:
				# 普通值，保持原值
				result.append(item)

		return result

	def mask_text(self, text: str) -> str:
		"""脱敏文本中的敏感信息

		使用正则表达式查找并替换文本中的敏感模式。

		Args:
			text: 要脱敏的文本

		Returns:
			脱敏后的文本
		"""
		result = text

		# 对每个敏感模式进行替换
		for pattern in self.sensitive_patterns:
			# 匹配 key=value 或 key: value 格式
			# 支持带引号和不带引号的值
			regex = re.compile(
				rf'({pattern}[\s]*[:=][\s]*)((["\'])([^"\']*)\3|([^\s,}}]+))',
				re.IGNORECASE,
			)
			result = regex.sub(
				lambda m: (
					f'{m.group(1)}{m.group(3) or ""}{self.mask_placeholder}{m.group(3) or ""}'
				),
				result,
			)

		return result


class ResourceAccessControl:
	"""Resource 访问控制器

	控制对 Resources 的访问权限，支持基于 URI 模式的访问控制。

	Example:
		>>> # 基本使用
		>>> control = ResourceAccessControl()
		>>> allowed = control.can_access('openapi://spec')
		>>>
		>>> # 限制特定资源访问
		>>> control = ResourceAccessControl(
		...     blocked_patterns=['openapi://admin/*'],
		...     allowed_patterns=['openapi://public/*', 'openapi://spec']
		... )
		>>> allowed = control.can_access('openapi://admin/users')
	"""

	def __init__(
		self,
		allowed_patterns: list[str] | None = None,
		blocked_patterns: list[str] | None = None,
		default_allow: bool = True,
	) -> None:
		"""初始化 Resource 访问控制器

		Args:
			allowed_patterns: 允许访问的 URI 模式列表，支持通配符 *
			blocked_patterns: 禁止访问的 URI 模式列表
			default_allow: 默认是否允许访问（当不匹配任何规则时）
		"""
		self.allowed_patterns = allowed_patterns or []
		self.blocked_patterns = blocked_patterns or []
		self.default_allow = default_allow

		# 将通配符模式转换为正则表达式
		self._allowed_regexes = [
			re.compile(self._pattern_to_regex(pattern))
			for pattern in self.allowed_patterns
		]
		self._blocked_regexes = [
			re.compile(self._pattern_to_regex(pattern))
			for pattern in self.blocked_patterns
		]

	def _pattern_to_regex(self, pattern: str) -> str:
		"""将通配符模式转换为正则表达式

		Args:
			pattern: 通配符模式，如 'openapi://admin/*'

		Returns:
			正则表达式字符串
		"""
		# 转义正则表达式特殊字符（除了 *）
		escaped = re.escape(pattern)
		# 将 \* 替换为正则表达式的 .*
		regex = escaped.replace(r'\*', '.*')
		return f'^{regex}$'

	def can_access(self, uri: str) -> bool:
		"""判断是否允许访问指定的 Resource

		Args:
			uri: Resource URI

		Returns:
			True 表示允许访问
		"""
		# 先检查是否在禁止列表中
		for regex in self._blocked_regexes:
			if regex.match(uri):
				logger.info(f'Resource access blocked by pattern: {uri}')
				return False

		# 如果有允许列表，检查是否在列表中
		if self._allowed_regexes:
			for regex in self._allowed_regexes:
				if regex.match(uri):
					return True
			# 有允许列表但不匹配任何模式
			logger.info(f'Resource access not in allowed patterns: {uri}')
			return False

		# 使用默认设置
		return self.default_allow


class AccessLogger:
	"""访问日志记录器

	记录工具调用的访问日志，包括时间、工具名、参数（脱敏后）等。

	Example:
		>>> logger = AccessLogger()
		>>> logger.log_tool_call('list_endpoints', {'path': '/api/users'})
		>>>
		>>> # 启用敏感信息脱敏
		>>> logger = AccessLogger(mask_sensitive=True)
		>>> logger.log_tool_call('get_endpoint', {'path': '/auth', 'token': 'secret'})
	"""

	def __init__(
		self,
		mask_sensitive: bool = True,
		masker: SensitiveDataMasker | None = None,
		log_level: int = logging.INFO,
		resource_access_control: ResourceAccessControl | None = None,
	) -> None:
		"""初始化访问日志记录器

		Args:
			mask_sensitive: 是否脱敏敏感信息
			masker: 自定义脱敏器，None 则使用默认配置
			log_level: 日志级别
			resource_access_control: Resource 访问控制器
		"""
		self.mask_sensitive = mask_sensitive
		self.masker = masker or SensitiveDataMasker()
		self.resource_access_control = resource_access_control
		self.logger = logging.getLogger(f'{__name__}.access')
		self.logger.setLevel(log_level)

	def can_access_resource(self, uri: str) -> bool:
		"""检查是否允许访问 Resource

		Args:
			uri: Resource URI

		Returns:
			True 表示允许访问
		"""
		if self.resource_access_control:
			return self.resource_access_control.can_access(uri)
		return True

	def log_tool_call(
		self,
		tool_name: str,
		arguments: dict[str, Any],
		result: str | None = None,
		error: str | None = None,
	) -> None:
		"""记录工具调用日志

		Args:
			tool_name: 工具名称
			arguments: 工具参数
			result: 执行结果（可选）
			error: 错误信息（可选）
		"""
		# 脱敏参数
		masked_args = (
			self.masker.mask_dict(arguments) if self.mask_sensitive else arguments
		)

		# 构建日志消息
		timestamp = datetime.now().isoformat()
		log_entry = {
			'timestamp': timestamp,
			'tool': tool_name,
			'arguments': masked_args,
		}

		if result is not None:
			log_entry['result'] = 'success'
		if error is not None:
			log_entry['error'] = error

		# 记录日志
		if error:
			self.logger.error(f'Tool call failed: {log_entry}')
		else:
			self.logger.info(f'Tool call: {log_entry}')

	def log_access_denied(
		self, tool_name: str, arguments: dict[str, Any], reason: str
	) -> None:
		"""记录访问拒绝日志

		Args:
			tool_name: 工具名称
			arguments: 工具参数
			reason: 拒绝原因
		"""
		# 脱敏参数
		masked_args = (
			self.masker.mask_dict(arguments) if self.mask_sensitive else arguments
		)

		# 构建日志消息
		timestamp = datetime.now().isoformat()
		log_entry = {
			'timestamp': timestamp,
			'tool': tool_name,
			'arguments': masked_args,
			'status': 'denied',
			'reason': reason,
		}

		# 记录警告日志
		self.logger.warning(f'Access denied: {log_entry}')

	def log_resource_access(
		self,
		uri: str,
		session_id: str | None = None,
		user_info: dict[str, Any] | None = None,
		duration: float | None = None,
		error: str | None = None
	) -> None:
		"""记录 Resource 访问日志

		Args:
			uri: 资源 URI
			session_id: 会话 ID（可选）
			user_info: 用户信息（可选）
			duration: 访问耗时（秒，可选）
			error: 错误信息（可选）
		"""
		# 构建日志消息
		timestamp = datetime.now().isoformat()
		log_entry = {
			'timestamp': timestamp,
			'resource': uri,
			'status': 'success' if error is None else 'failed',
		}

		# 添加可选信息
		if session_id:
			log_entry['session_id'] = session_id
		if user_info:
			log_entry['user'] = user_info
		if duration is not None:
			log_entry['duration_ms'] = round(duration * 1000, 2)
		if error is not None:
			log_entry['error'] = error

		# 记录日志
		if error:
			self.logger.error(f'Resource access failed: {log_entry}')
		else:
			self.logger.info(f'Resource access: {log_entry}')

	def log_resource_access_denied(
		self,
		uri: str,
		reason: str,
		session_id: str | None = None,
		user_info: dict[str, Any] | None = None
	) -> None:
		"""记录 Resource 访问拒绝日志

		Args:
			uri: 资源 URI
			reason: 拒绝原因
			session_id: 会话 ID（可选）
			user_info: 用户信息（可选）
		"""
		# 构建日志消息
		timestamp = datetime.now().isoformat()
		log_entry = {
			'timestamp': timestamp,
			'resource': uri,
			'status': 'denied',
			'reason': reason,
		}

		# 添加可选信息
		if session_id:
			log_entry['session_id'] = session_id
		if user_info:
			log_entry['user'] = user_info

		# 记录警告日志
		self.logger.warning(f'Resource access denied: {log_entry}')
