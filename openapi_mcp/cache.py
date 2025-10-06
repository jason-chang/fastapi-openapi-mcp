"""
OpenAPI MCP Server 缓存机制
"""

import time
from typing import Any


class CacheEntry:
	"""缓存条目

	存储缓存值和过期时间戳。

	Attributes:
		value: 缓存的值
		expire_at: 过期时间戳（秒），None 表示永不过期
	"""

	__slots__ = ('value', 'expire_at')

	def __init__(self, value: Any, expire_at: float | None) -> None:
		"""初始化缓存条目

		Args:
			value: 要缓存的值
			expire_at: 过期时间戳（秒），None 表示永不过期
		"""
		self.value = value
		self.expire_at = expire_at

	def is_expired(self) -> bool:
		"""检查缓存是否已过期

		Returns:
			True 表示已过期，False 表示未过期
		"""
		if self.expire_at is None:
			return False
		return time.time() > self.expire_at


class OpenApiCache:
	"""OpenAPI 缓存管理器

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
