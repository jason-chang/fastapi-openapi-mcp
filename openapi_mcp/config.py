"""
MCP Server 配置管理

提供全面的配置管理功能，包括 Resources 设置、缓存策略、性能监控等。
"""

import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from mcp.types import Tool
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
	"""日志级别"""
	DEBUG = "DEBUG"
	INFO = "INFO"
	WARNING = "WARNING"
	ERROR = "ERROR"
	CRITICAL = "CRITICAL"


class CacheStrategy(str, Enum):
	"""缓存策略"""
	NONE = "none"           # 不缓存
	BASIC = "basic"         # 基础缓存
	LRU = "lru"            # LRU 缓存
	MULTI_LEVEL = "multi_level"  # 多级缓存


class PerformanceLevel(str, Enum):
	"""性能级别"""
	LOW = "low"           # 低性能模式
	MEDIUM = "medium"     # 中等性能模式
	HIGH = "high"         # 高性能模式
	MAXIMUM = "maximum"   # 最大性能模式


class ResourcesConfig(BaseModel):
	"""Resources 配置"""

	enabled: bool = Field(default=True, description="是否启用 Resources")
	cache_ttl: int = Field(
		default=300,
		description="Resources 缓存时间（秒）",
		ge=0
	)
	max_cache_size: int = Field(
		default=1000,
		description="Resources 最大缓存条目数",
		ge=1
	)
	access_control_enabled: bool = Field(
		default=False,
		description="是否启用 Resource 访问控制"
	)
	allowed_patterns: list[str] = Field(
		default_factory=list,
		description="允许的 Resource URI 模式"
	)
	blocked_patterns: list[str] = Field(
		default_factory=list,
		description="禁止的 Resource URI 模式"
	)


class CacheConfig(BaseModel):
	"""缓存配置"""

	strategy: CacheStrategy = Field(
		default=CacheStrategy.LRU,
		description="缓存策略"
	)
	l1_size: int = Field(
		default=100,
		description="L1 缓存大小",
		ge=1
	)
	l2_size: int = Field(
		default=1000,
		description="L2 缓存大小",
		ge=0
	)
	l1_ttl: int | None = Field(
		default=60,
		description="L1 缓存 TTL（秒）",
		ge=0
	)
	l2_ttl: int | None = Field(
		default=3600,
		description="L2 缓存 TTL（秒）",
		ge=0
	)
	enable_l2: bool = Field(
		default=True,
		description="是否启用 L2 缓存"
	)
	cleanup_interval: int = Field(
		default=300,
		description="缓存清理间隔（秒）",
		ge=60
	)


class PerformanceConfig(BaseModel):
	"""性能配置"""

	level: PerformanceLevel = Field(
		default=PerformanceLevel.MEDIUM,
		description="性能级别"
	)
	monitoring_enabled: bool = Field(
		default=True,
		description="是否启用性能监控"
	)
	max_tracked_operations: int = Field(
		default=100,
		description="最大跟踪操作数",
		ge=1
	)
	slow_operation_threshold: float = Field(
		default=1.0,
		description="慢操作阈值（秒）",
		ge=0.1
	)
	memory_limit_mb: int | None = Field(
		default=100,
		description="内存限制（MB）",
		ge=1
	)
	enable_profiling: bool = Field(
		default=False,
		description="是否启用性能分析"
	)


class SecurityConfig(BaseModel):
	"""安全配置"""

	auth_required: bool = Field(default=False, description="是否需要认证")
	allowed_origins: list[str] = Field(
		default_factory=lambda: ['*'],
		description="允许的 CORS 来源"
	)
	enable_access_logging: bool = Field(
		default=False,
		description="是否启用访问日志记录"
	)
	mask_sensitive_data: bool = Field(
		default=True,
		description="是否脱敏敏感数据"
	)
	custom_sensitive_patterns: list[str] = Field(
		default_factory=list,
		description="自定义敏感字段模式"
	)
	tool_filter_enabled: bool = Field(
		default=False,
		description="是否启用工具过滤"
	)
	path_patterns: list[str] = Field(
		default_factory=list,
		description="允许的路径模式列表，支持通配符"
	)
	allowed_tags: list[str] = Field(
		default_factory=list,
		description="允许的标签列表，为空表示允许所有"
	)
	blocked_tags: list[str] = Field(
		default_factory=list,
		description="禁止的标签列表"
	)

	@field_validator('allowed_origins')
	def validate_origins(cls, v):
		"""验证 CORS 来源"""
		if not v or '*' in v:
			return v
		# 简单的 URL 格式验证
		for origin in v:
			if not (origin.startswith('http://') or origin.startswith('https://')):
				raise ValueError(f"Invalid origin format: {origin}")
		return v


class OpenApiMcpConfig(BaseModel):
	"""OpenAPI MCP Server 配置"""

	# 基础配置
	debug: bool = Field(default=False, description="是否启用调试模式")
	log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")

	# 路由配置
	prefix: str = Field(default='/openapi-mcp', description='MCP 路由前缀')
	include_sse: bool = Field(default=True, description='是否包含 SSE 端点')
	include_rest_api: bool = Field(
		default=True, description='是否包含 REST API（用于调试）'
	)

	# 输出格式配置
	output_format: str = Field(
		default='markdown', description='输出格式', pattern='^(markdown|json|plain)$'
	)
	max_output_length: int = Field(
		default=10000, description='最大输出长度（字符）', gt=0
	)

	# 子配置
	resources: ResourcesConfig = Field(
		default_factory=ResourcesConfig,
		description="Resources 配置"
	)
	cache: CacheConfig = Field(
		default_factory=CacheConfig,
		description="缓存配置"
	)
	performance: PerformanceConfig = Field(
		default_factory=PerformanceConfig,
		description="性能配置"
	)
	security: SecurityConfig = Field(
		default_factory=SecurityConfig,
		description="安全配置"
	)

	# 自定义扩展
	custom_tools: list[Tool] = Field(default_factory=list, description='自定义 Tools')
	tool_filter: Callable[[str, dict[str, Any]], bool] | None = Field(
		default=None, description='Tool 过滤器函数，接收工具名和参数，返回是否允许'
	)

	# 兼容性字段（已弃用，使用子配置替代）
	@property
	def cache_enabled(self) -> bool:
		"""兼容性属性：是否启用缓存"""
		return self.cache.strategy != CacheStrategy.NONE

	@property
	def cache_ttl(self) -> int:
		"""兼容性属性：缓存 TTL"""
		return self.cache.l1_ttl or 300

	@property
	def auth_required(self) -> bool:
		"""兼容性属性：是否需要认证"""
		return self.security.auth_required

	@property
	def allowed_origins(self) -> list[str]:
		"""兼容性属性：允许的 CORS 来源"""
		return self.security.allowed_origins

	@property
	def enable_access_logging(self) -> bool:
		"""兼容性属性：是否启用访问日志记录"""
		return self.security.enable_access_logging

	@property
	def mask_sensitive_data(self) -> bool:
		"""兼容性属性：是否脱敏敏感数据"""
		return self.security.mask_sensitive_data

	@property
	def path_patterns(self) -> list[str]:
		"""兼容性属性：允许的路径模式"""
		return self.security.path_patterns

	@property
	def allowed_tags(self) -> list[str]:
		"""兼容性属性：允许的标签"""
		return self.security.allowed_tags

	@property
	def blocked_tags(self) -> list[str]:
		"""兼容性属性：禁止的标签"""
		return self.security.blocked_tags

	# Pydantic 配置
	model_config = ConfigDict(arbitrary_types_allowed=True)

	def apply_performance_level(self) -> None:
		"""根据性能级别应用配置"""
		level = self.performance.level

		if level == PerformanceLevel.LOW:
			# 低性能模式：最小缓存，无监控
			self.cache.strategy = CacheStrategy.BASIC
			self.cache.l1_size = 50
			self.cache.l2_size = 0
			self.cache.enable_l2 = False
			self.performance.monitoring_enabled = False
			self.performance.max_tracked_operations = 10
			self.resources.max_cache_size = 100

		elif level == PerformanceLevel.MEDIUM:
			# 中等性能模式：默认配置
			self.cache.strategy = CacheStrategy.LRU
			self.cache.l1_size = 100
			self.cache.l2_size = 1000
			self.performance.monitoring_enabled = True
			self.performance.max_tracked_operations = 100
			self.resources.max_cache_size = 500

		elif level == PerformanceLevel.HIGH:
			# 高性能模式：更大的缓存，更多监控
			self.cache.strategy = CacheStrategy.MULTI_LEVEL
			self.cache.l1_size = 200
			self.cache.l2_size = 2000
			self.performance.monitoring_enabled = True
			self.performance.max_tracked_operations = 200
			self.resources.max_cache_size = 1000

		elif level == PerformanceLevel.MAXIMUM:
			# 最大性能模式：最大缓存，全面监控
			self.cache.strategy = CacheStrategy.MULTI_LEVEL
			self.cache.l1_size = 500
			self.cache.l2_size = 5000
			self.performance.monitoring_enabled = True
			self.performance.max_tracked_operations = 500
			self.performance.enable_profiling = True
			self.resources.max_cache_size = 2000

		logger.info(f"Applied performance level: {level.value}")

	def validate_config(self) -> list[str]:
		"""验证配置并返回警告列表

		Returns:
			配置警告列表
		"""
		warnings = []

		# 检查缓存配置
		if self.cache.strategy == CacheStrategy.MULTI_LEVEL and not self.cache.enable_l2:
			warnings.append("Multi-level cache strategy enabled but L2 cache is disabled")

		if self.cache.l1_size > 10000:
			warnings.append(f"Large L1 cache size ({self.cache.l1_size}) may consume significant memory")

		# 检查安全配置
		if not self.security.allowed_origins or '*' in self.security.allowed_origins:
			if self.security.auth_required:
				warnings.append("Authentication required but CORS allows all origins")

		# 检查性能配置
		if self.performance.level == PerformanceLevel.MAXIMUM and self.performance.memory_limit_mb and self.performance.memory_limit_mb < 200:
			warnings.append("Maximum performance level with low memory limit may cause issues")

		# 检查 Resources 配置
		if self.resources.enabled and not self.resources.cache_ttl:
			warnings.append("Resources enabled but cache TTL is 0, may impact performance")

		return warnings

	def get_effective_config(self) -> dict[str, Any]:
		"""获取生效的配置（包含性能级别调整后的值）

		Returns:
			生效的配置字典
		"""
		# 应用性能级别
		self.apply_performance_level()

		# 转换为字典
		config_dict = self.model_dump()

		# 添加验证警告
		warnings = self.validate_config()
		if warnings:
			config_dict['_warnings'] = warnings

		return config_dict


class ConfigManager:
	"""配置管理器

	支持动态配置更新、配置验证和配置监听。
	"""

	def __init__(self, initial_config: OpenApiMcpConfig | None = None) -> None:
		"""初始化配置管理器

		Args:
			initial_config: 初始配置，None 使用默认配置
		"""
		self._config = initial_config or OpenApiMcpConfig()
		self._listeners: list[Callable[[OpenApiMcpConfig], None]] = []
		self._config_history: list[dict[str, Any]] = []
		self._max_history = 100

	@property
	def config(self) -> OpenApiMcpConfig:
		"""获取当前配置"""
		return self._config

	def update_config(self, new_config: dict[str, Any]) -> list[str]:
		"""更新配置

		Args:
			new_config: 新配置字典

		Returns:
			配置警告列表

		Raises:
			ValidationError: 当配置无效时
		"""
		# 保存当前配置到历史
		current_config_dict = self._config.model_dump()
		self._config_history.append(current_config_dict)

		# 限制历史记录数量
		if len(self._config_history) > self._max_history:
			self._config_history.pop(0)

		try:
			# 创建新的配置对象
			updated_config = self._config.model_copy(update=new_config)

			# 验证配置
			warnings = updated_config.validate_config()

			# 更新配置
			self._config = updated_config

			# 通知监听器
			for listener in self._listeners:
				try:
					listener(self._config)
				except Exception as e:
					logger.error(f"Config listener error: {e}")

			logger.info("Configuration updated successfully")
			for warning in warnings:
				logger.warning(f"Configuration warning: {warning}")

			return warnings

		except Exception as e:
			# 恢复之前的配置
			logger.error(f"Configuration update failed: {e}")
			raise

	def add_listener(self, listener: Callable[[OpenApiMcpConfig], None]) -> None:
		"""添加配置变更监听器

		Args:
			listener: 监听器函数
		"""
		if listener not in self._listeners:
			self._listeners.append(listener)

	def remove_listener(self, listener: Callable[[OpenApiMcpConfig], None]) -> None:
		"""移除配置变更监听器

		Args:
			listener: 监听器函数
		"""
		if listener in self._listeners:
			self._listeners.remove(listener)

	def get_config_history(self) -> list[dict[str, Any]]:
		"""获取配置历史

		Returns:
			配置历史列表
		"""
		return self._config_history.copy()

	def restore_config(self, index: int = -1) -> list[str]:
		"""恢复历史配置

		Args:
			index: 历史索引，-1 表示上一个配置

		Returns:
			配置警告列表

		Raises:
			IndexError: 当索引无效时
		"""
		if not self._config_history:
			raise ValueError("No configuration history available")

		if index < -len(self._config_history) or index >= len(self._config_history):
			raise IndexError(f"Invalid config history index: {index}")

		historical_config = self._config_history[index]
		return self.update_config(historical_config)

	def reset_to_defaults(self) -> list[str]:
		"""重置为默认配置

		Returns:
			配置警告列表
		"""
		default_config = OpenApiMcpConfig()
		return self.update_config(default_config.model_dump())

	def get_effective_config(self) -> dict[str, Any]:
		"""获取生效的配置

		Returns:
			生效的配置字典
		"""
		return self._config.get_effective_config()

	def export_config(self) -> dict[str, Any]:
		"""导出配置（包含敏感信息）

		Returns:
			完整配置字典
		"""
		return self._config.model_dump()

	def export_safe_config(self) -> dict[str, Any]:
		"""导出安全配置（不包含敏感信息）

		Returns:
			安全配置字典
		"""
		config_dict = self._config.model_dump()

		# 移除敏感信息
		sensitive_keys = [
			'custom_tools',
			'tool_filter',
			'security.custom_sensitive_patterns'
		]

		for key in sensitive_keys:
			if key in config_dict:
				config_dict[key] = '<REDACTED>'

		return config_dict

	def import_config(self, config_data: dict[str, Any], safe: bool = True) -> list[str]:
		"""导入配置

		Args:
			config_data: 配置数据
			safe: 是否为安全导入（跳过敏感字段）

		Returns:
			配置警告列表
		"""
		if safe:
			# 移除可能的敏感字段
			sensitive_keys = [
				'custom_tools',
				'tool_filter',
				'custom_sensitive_patterns'
			]

			for key in sensitive_keys:
				config_data.pop(key, None)

		return self.update_config(config_data)

	def validate_config(self, config_data: dict[str, Any]) -> list[str]:
		"""验证配置数据

		Args:
			config_data: 配置数据

		Returns:
			验证警告列表
		"""
		try:
			temp_config = OpenApiMcpConfig(**config_data)
			return temp_config.validate_config()
		except Exception as e:
			return [f"Configuration validation failed: {e}"]


# 全局配置管理器实例
_global_config_manager = ConfigManager()


def get_global_config_manager() -> ConfigManager:
	"""获取全局配置管理器

	Returns:
		全局配置管理器实例
	"""
	return _global_config_manager


def get_config() -> OpenApiMcpConfig:
	"""获取当前全局配置

	Returns:
		当前配置
	"""
	return _global_config_manager.config


def update_config(config_data: dict[str, Any]) -> list[str]:
	"""更新全局配置

	Args:
		config_data: 配置数据

	Returns:
		配置警告列表
	"""
	return _global_config_manager.update_config(config_data)
