"""
OpenAPI MCP Server 缓存机制

提供多级缓存策略、LRU 缓存、性能监控等高级缓存功能。
"""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
	"""缓存统计信息"""

	hits: int = 0
	misses: int = 0
	evictions: int = 0
	total_sets: int = 0
	total_gets: int = 0

	@property
	def hit_rate(self) -> float:
		"""缓存命中率"""
		if self.total_gets == 0:
			return 0.0
		return self.hits / self.total_gets

	def reset(self) -> None:
		"""重置统计信息"""
		self.hits = 0
		self.misses = 0
		self.evictions = 0
		self.total_sets = 0
		self.total_gets = 0


@dataclass
class CacheEntry:
	"""缓存条目

	存储缓存值和过期时间戳。

	Attributes:
		value: 缓存的值
		expire_at: 过期时间戳（秒），None 表示永不过期
		created_at: 创建时间戳
		access_count: 访问次数
		last_accessed: 最后访问时间
	"""

	value: Any
	expire_at: float | None
	created_at: float
	access_count: int
	last_accessed: float

	def __init__(self, value: Any, expire_at: float | None) -> None:
		"""初始化缓存条目

		Args:
			value: 要缓存的值
			expire_at: 过期时间戳（秒），None 表示永不过期
		"""
		self.value = value
		self.expire_at = expire_at
		self.created_at = time.time()
		self.access_count = 0
		self.last_accessed = self.created_at

	def touch(self) -> None:
		"""更新访问信息"""
		self.access_count += 1
		self.last_accessed = time.time()

	def is_expired(self) -> bool:
		"""检查缓存是否已过期

		Returns:
			True 表示已过期，False 表示未过期
		"""
		if self.expire_at is None:
			return False
		return time.time() > self.expire_at

	def get_age(self) -> float:
		"""获取缓存年龄（秒）

		Returns:
			缓存年龄
		"""
		return time.time() - self.created_at

	def get_ttl(self) -> float:
		"""获取剩余存活时间（秒）

		Returns:
			剩余存活时间，如果永不过期返回 float('inf')
		"""
		if self.expire_at is None:
			return float('inf')
		return max(0, self.expire_at - time.time())


class LRUCache:
	"""LRU (Least Recently Used) 缓存实现

	当缓存达到最大容量时，自动移除最久未使用的条目。

	Example:
		>>> cache = LRUCache(max_size=100)
		>>> cache.set('key1', 'value1')
		>>> result = cache.get('key1')
		>>> stats = cache.get_stats()
	"""

	def __init__(self, max_size: int = 1000, default_ttl: int | None = None) -> None:
		"""初始化 LRU 缓存

		Args:
			max_size: 最大缓存条目数
			default_ttl: 默认 TTL（秒），None 表示永不过期
		"""
		if max_size <= 0:
			raise ValueError(f'max_size 必须大于 0: {max_size}')

		self.max_size = max_size
		self.default_ttl = default_ttl
		self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
		self._stats = CacheStats()

	def get(self, key: str) -> Any | None:
		"""获取缓存值

		Args:
			key: 缓存键

		Returns:
			缓存的值，如果不存在或已过期则返回 None
		"""
		self._stats.total_gets += 1

		if key not in self._cache:
			self._stats.misses += 1
			return None

		entry = self._cache[key]

		# 检查是否过期
		if entry.is_expired():
			del self._cache[key]
			self._stats.misses += 1
			logger.debug(f'Cache entry expired: {key}')
			return None

		# 更新访问时间和位置（移到末尾）
		entry.touch()
		self._cache.move_to_end(key)
		self._stats.hits += 1

		return entry.value

	def set(self, key: str, value: Any, ttl: int | None = None) -> None:
		"""设置缓存值

		Args:
			key: 缓存键
			value: 要缓存的值
			ttl: 过期时间（秒），None 使用默认 TTL
		"""
		if ttl is None:
			ttl = self.default_ttl

		if ttl is not None and ttl < 0:
			raise ValueError(f'TTL 不能为负数: {ttl}')

		# 计算过期时间戳
		expire_at = None if ttl is None else time.time() + ttl

		# 如果键已存在，更新值
		if key in self._cache:
			self._cache[key] = CacheEntry(value, expire_at)
			self._cache.move_to_end(key)
		else:
			# 检查是否需要驱逐条目
			while len(self._cache) >= self.max_size:
				self._evict_lru()

			self._cache[key] = CacheEntry(value, expire_at)

		self._stats.total_sets += 1

	def _evict_lru(self) -> None:
		"""驱逐最久未使用的条目"""
		if self._cache:
			lru_key, lru_entry = self._cache.popitem(last=False)
			self._stats.evictions += 1
			logger.debug(f'Evicted LRU cache entry: {lru_key}')

	def invalidate(self, key: str) -> bool:
		"""清除指定的缓存项

		Args:
			key: 要清除的缓存键

		Returns:
			如果缓存项存在并被删除返回 True，否则返回 False
		"""
		if key in self._cache:
			del self._cache[key]
			return True
		return False

	def clear(self) -> None:
		"""清空所有缓存"""
		self._cache.clear()
		self._stats.reset()

	def cleanup_expired(self) -> int:
		"""清理过期的缓存项

		Returns:
			清理的条目数量
		"""
		expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

		for key in expired_keys:
			del self._cache[key]

		if expired_keys:
			logger.debug(f'Cleaned up {len(expired_keys)} expired cache entries')

		return len(expired_keys)

	def get_stats(self) -> dict[str, Any]:
		"""获取缓存统计信息

		Returns:
			统计信息字典
		"""
		return {
			'hits': self._stats.hits,
			'misses': self._stats.misses,
			'hit_rate': self._stats.hit_rate,
			'evictions': self._stats.evictions,
			'total_sets': self._stats.total_sets,
			'total_gets': self._stats.total_gets,
			'size': len(self._cache),
			'max_size': self.max_size,
		}

	def __len__(self) -> int:
		"""返回当前缓存条目数量"""
		return len(self._cache)

	def __contains__(self, key: str) -> bool:
		"""检查缓存键是否存在且未过期"""
		return self.get(key) is not None


class MultiLevelCache:
	"""多级缓存系统

	提供 L1（内存）和 L2（持久化）两级缓存。

	Example:
		>>> cache = MultiLevelCache(
		...     l1_size=100,    # L1 缓存大小
		...     l2_size=1000,   # L2 缓存大小
		...     l1_ttl=60,      # L1 缓存 TTL
		...     l2_ttl=3600     # L2 缓存 TTL
		... )
		>>> cache.set('key', 'value')
		>>> result = cache.get('key')
	"""

	def __init__(
		self,
		l1_size: int = 100,
		l2_size: int = 1000,
		l1_ttl: int | None = 60,
		l2_ttl: int | None = 3600,
		enable_l2: bool = True,
	) -> None:
		"""初始化多级缓存

		Args:
			l1_size: L1 缓存最大条目数
			l2_size: L2 缓存最大条目数
			l1_ttl: L1 缓存默认 TTL
			l2_ttl: L2 缓存默认 TTL
			enable_l2: 是否启用 L2 缓存
		"""
		self.l1_cache = LRUCache(max_size=l1_size, default_ttl=l1_ttl)
		self.enable_l2 = enable_l2

		if enable_l2:
			self.l2_cache = LRUCache(max_size=l2_size, default_ttl=l2_ttl)
		else:
			self.l2_cache = None

		self._total_hits = 0
		self._total_misses = 0

	def get(self, key: str) -> Any | None:
		"""获取缓存值（先查 L1，再查 L2）

		Args:
			key: 缓存键

		Returns:
			缓存的值，如果不存在则返回 None
		"""
		# 先查 L1 缓存
		value = self.l1_cache.get(key)
		if value is not None:
			self._total_hits += 1
			return value

		# 再查 L2 缓存
		if self.l2_cache:
			value = self.l2_cache.get(key)
			if value is not None:
				self._total_hits += 1
				# 将 L2 的数据提升到 L1
				self.l1_cache.set(key, value)
				return value

		self._total_misses += 1
		return None

	def set(self, key: str, value: Any, ttl: int | None = None) -> None:
		"""设置缓存值（同时设置 L1 和 L2）

		Args:
			key: 缓存键
			value: 要缓存的值
			ttl: 过期时间（秒），None 使用默认 TTL
		"""
		self.l1_cache.set(key, value, ttl)
		if self.l2_cache:
			self.l2_cache.set(key, value, ttl)

	def invalidate(self, key: str) -> bool:
		"""清除指定的缓存项（同时清除 L1 和 L2）

		Args:
			key: 要清除的缓存键

		Returns:
			如果任一级缓存存在并被删除返回 True
		"""
		l1_removed = self.l1_cache.invalidate(key)
		l2_removed = False

		if self.l2_cache:
			l2_removed = self.l2_cache.invalidate(key)

		return l1_removed or l2_removed

	def clear(self) -> None:
		"""清空所有缓存"""
		self.l1_cache.clear()
		if self.l2_cache:
			self.l2_cache.clear()
		self._total_hits = 0
		self._total_misses = 0

	def cleanup_expired(self) -> int:
		"""清理过期的缓存项

		Returns:
			清理的条目总数
		"""
		total = self.l1_cache.cleanup_expired()
		if self.l2_cache:
			total += self.l2_cache.cleanup_expired()
		return total

	def get_stats(self) -> dict[str, Any]:
		"""获取缓存统计信息

		Returns:
			统计信息字典
		"""
		stats = {
			'l1_cache': self.l1_cache.get_stats(),
			'total_hits': self._total_hits,
			'total_misses': self._total_misses,
			'overall_hit_rate': (
				self._total_hits / (self._total_hits + self._total_misses)
				if (self._total_hits + self._total_misses) > 0
				else 0.0
			),
		}

		if self.l2_cache:
			stats['l2_cache'] = self.l2_cache.get_stats()

		return stats


class ResourceCache:
	"""专门的 Resource 缓存

	为 OpenAPI Resources 提供智能缓存策略。

	Example:
		>>> cache = ResourceCache()
		>>> # 缓存 OpenAPI spec
		>>> cache.set_spec({'openapi': '3.0.0', ...})
		>>> spec = cache.get_spec()
		>>>
		>>> # 缓存端点信息
		>>> cache.set_endpoints([{'path': '/users', ...}, ...])
		>>> endpoints = cache.get_endpoints()
	"""

	def __init__(
		self,
		spec_ttl: int = 3600,  # OpenAPI spec 缓存 1 小时
		endpoints_ttl: int = 1800,  # 端点列表缓存 30 分钟
		models_ttl: int = 900,  # 模型信息缓存 15 分钟
		tags_ttl: int = 1800,  # 标签信息缓存 30 分钟
	) -> None:
		"""初始化 Resource 缓存

		Args:
			spec_ttl: OpenAPI spec 缓存时间
			endpoints_ttl: 端点列表缓存时间
			models_ttl: 模型信息缓存时间
			tags_ttl: 标签信息缓存时间
		"""
		self.cache = LRUCache(max_size=500)
		self.spec_ttl = spec_ttl
		self.endpoints_ttl = endpoints_ttl
		self.models_ttl = models_ttl
		self.tags_ttl = tags_ttl

	def _make_key(self, resource_type: str, identifier: str = '') -> str:
		"""生成缓存键

		Args:
			resource_type: 资源类型
			identifier: 标识符

		Returns:
			缓存键
		"""
		key = f'resource:{resource_type}'
		if identifier:
			key += f':{identifier}'
		return hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()

	def set_spec(self, spec: dict[str, Any]) -> None:
		"""缓存 OpenAPI spec

		Args:
			spec: OpenAPI 规范文档
		"""
		key = self._make_key('spec')
		self.cache.set(key, spec, self.spec_ttl)

	def get_spec(self) -> dict[str, Any] | None:
		"""获取缓存的 OpenAPI spec

		Returns:
			OpenAPI 规范文档，如果不存在返回 None
		"""
		key = self._make_key('spec')
		return self.cache.get(key)

	def set_endpoints(self, endpoints: list[dict[str, Any]]) -> None:
		"""缓存端点列表

		Args:
			endpoints: 端点列表
		"""
		key = self._make_key('endpoints')
		self.cache.set(key, endpoints, self.endpoints_ttl)

	def get_endpoints(self) -> list[dict[str, Any]] | None:
		"""获取缓存的端点列表

		Returns:
			端点列表，如果不存在返回 None
		"""
		key = self._make_key('endpoints')
		return self.cache.get(key)

	def set_model(self, model_name: str, model_def: dict[str, Any]) -> None:
		"""缓存模型定义

		Args:
			model_name: 模型名称
			model_def: 模型定义
		"""
		key = self._make_key('model', model_name)
		self.cache.set(key, model_def, self.models_ttl)

	def get_model(self, model_name: str) -> dict[str, Any] | None:
		"""获取缓存的模型定义

		Args:
			model_name: 模型名称

		Returns:
			模型定义，如果不存在返回 None
		"""
		key = self._make_key('model', model_name)
		return self.cache.get(key)

	def set_tag_endpoints(self, tag: str, endpoints: list[dict[str, Any]]) -> None:
		"""缓存标签关联的端点

		Args:
			tag: 标签名
			endpoints: 端点列表
		"""
		key = self._make_key('tag_endpoints', tag)
		self.cache.set(key, endpoints, self.tags_ttl)

	def get_tag_endpoints(self, tag: str) -> list[dict[str, Any]] | None:
		"""获取缓存中标签关联的端点

		Args:
			tag: 标签名

		Returns:
			端点列表，如果不存在返回 None
		"""
		key = self._make_key('tag_endpoints', tag)
		return self.cache.get(key)

	def invalidate_by_type(self, resource_type: str) -> int:
		"""按资源类型失效缓存

		Args:
			resource_type: 资源类型

		Returns:
			失效的缓存项数量
		"""
		# 由于使用哈希键，无法直接按类型查找
		# 这里简化为清空所有缓存
		self.cache.clear()
		return len(self.cache)

	def get_stats(self) -> dict[str, Any]:
		"""获取缓存统计信息

		Returns:
			统计信息字典
		"""
		return self.cache.get_stats()

	def clear(self) -> None:
		"""清空所有缓存"""
		self.cache.clear()


class OpenApiCache:
	"""OpenAPI 缓存管理器（兼容性包装器）

	提供基于 TTL（Time To Live）的缓存机制，支持：
	- 设置缓存项及其过期时间
	- 获取缓存项（自动过滤过期项）
	- 手动清除指定缓存
	- 清空所有缓存

	Example:
		>>> cache = OpenApiCache()
		>>> cache.set('key1', {'data': 'value'}, ttl=60)
		>>> result = cache.get('key1')
		>>> cache.invalidate('key1')
		>>> cache.clear()
	"""

	def __init__(self) -> None:
		"""初始化缓存管理器"""
		self._cache: dict[str, CacheEntry] = {}

	def get(self, key: str) -> Any | None:
		"""获取缓存值

		如果缓存不存在或已过期，返回 None。
		过期的缓存项会被自动删除。

		Args:
			key: 缓存键

		Returns:
			缓存的值，如果不存在或已过期则返回 None
		"""
		if key not in self._cache:
			return None

		entry = self._cache[key]

		# 检查是否过期
		if entry.is_expired():
			del self._cache[key]
			return None

		return entry.value

	def set(self, key: str, value: Any, ttl: int | None = None) -> None:
		"""设置缓存值

		Args:
			key: 缓存键
			value: 要缓存的值
			ttl: 过期时间（秒），None 表示永不过期，0 表示立即过期

		Raises:
			ValueError: 当 ttl 为负数时
		"""
		if ttl is not None and ttl < 0:
			raise ValueError(f'TTL 不能为负数: {ttl}')

		# 计算过期时间戳
		expire_at = None if ttl is None else time.time() + ttl

		self._cache[key] = CacheEntry(value, expire_at)

	def invalidate(self, key: str) -> bool:
		"""清除指定的缓存项

		Args:
			key: 要清除的缓存键

		Returns:
			如果缓存项存在并被删除返回 True，否则返回 False
		"""
		if key in self._cache:
			del self._cache[key]
			return True
		return False

	def clear(self) -> None:
		"""清空所有缓存"""
		self._cache.clear()

	def __len__(self) -> int:
		"""返回当前缓存项数量（包括已过期但未清理的项）

		Returns:
			缓存项数量
		"""
		return len(self._cache)

	def __contains__(self, key: str) -> bool:
		"""检查缓存键是否存在且未过期

		Args:
			key: 缓存键

		Returns:
			如果键存在且未过期返回 True，否则返回 False
		"""
		return self.get(key) is not None
