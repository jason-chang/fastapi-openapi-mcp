"""
测试缓存机制
"""

import time

import pytest

from openapi_mcp.cache import (
	CacheEntry,
	CacheStats,
	LRUCache,
	MultiLevelCache,
	OpenApiCache,
	ResourceCache,
)


class TestCacheEntry:
	"""测试 CacheEntry 类"""

	def test_cache_entry_without_expiry(self) -> None:
		"""测试永不过期的缓存条目"""
		entry = CacheEntry('test_value', None)

		assert entry.value == 'test_value'
		assert entry.expire_at is None
		assert not entry.is_expired()

	def test_cache_entry_with_future_expiry(self) -> None:
		"""测试未来过期的缓存条目"""
		future_time = time.time() + 100
		entry = CacheEntry('test_value', future_time)

		assert entry.value == 'test_value'
		assert entry.expire_at == future_time
		assert not entry.is_expired()

	def test_cache_entry_with_past_expiry(self) -> None:
		"""测试已过期的缓存条目"""
		past_time = time.time() - 1
		entry = CacheEntry('test_value', past_time)

		assert entry.value == 'test_value'
		assert entry.is_expired()


class TestOpenApiCache:
	"""测试 OpenApiCache 类"""

	def test_cache_initialization(self) -> None:
		"""测试缓存初始化"""
		cache = OpenApiCache()

		assert len(cache) == 0
		assert 'any_key' not in cache

	def test_set_and_get_without_ttl(self) -> None:
		"""测试不设置 TTL 的缓存存取"""
		cache = OpenApiCache()
		test_data = {'key': 'value', 'number': 42}

		cache.set('test_key', test_data)
		result = cache.get('test_key')

		assert result == test_data
		assert len(cache) == 1
		assert 'test_key' in cache

	def test_set_and_get_with_ttl(self) -> None:
		"""测试设置 TTL 的缓存存取"""
		cache = OpenApiCache()
		cache.set('test_key', 'test_value', ttl=60)

		result = cache.get('test_key')
		assert result == 'test_value'

	def test_get_nonexistent_key(self) -> None:
		"""测试获取不存在的键"""
		cache = OpenApiCache()

		result = cache.get('nonexistent')
		assert result is None

	def test_ttl_expiry(self) -> None:
		"""测试 TTL 过期"""
		cache = OpenApiCache()
		cache.set('test_key', 'test_value', ttl=1)

		# 立即获取，应该存在
		assert cache.get('test_key') == 'test_value'

		# 等待过期
		time.sleep(1.1)

		# 获取应该返回 None，且缓存项被删除
		assert cache.get('test_key') is None
		assert len(cache) == 0

	def test_ttl_zero_expires_immediately(self) -> None:
		"""测试 TTL=0 立即过期"""
		cache = OpenApiCache()
		cache.set('test_key', 'test_value', ttl=0)

		# 立即尝试获取，应该已经过期
		# 注意：由于 time.time() 的精度，可能需要等待一小段时间
		time.sleep(0.01)
		assert cache.get('test_key') is None

	def test_set_with_negative_ttl_raises_error(self) -> None:
		"""测试负数 TTL 抛出异常"""
		cache = OpenApiCache()

		with pytest.raises(ValueError, match='TTL 不能为负数'):
			cache.set('test_key', 'test_value', ttl=-1)

	def test_invalidate_existing_key(self) -> None:
		"""测试清除存在的缓存项"""
		cache = OpenApiCache()
		cache.set('test_key', 'test_value')

		result = cache.invalidate('test_key')
		assert result is True
		assert cache.get('test_key') is None
		assert len(cache) == 0

	def test_invalidate_nonexistent_key(self) -> None:
		"""测试清除不存在的缓存项"""
		cache = OpenApiCache()

		result = cache.invalidate('nonexistent')
		assert result is False

	def test_clear_all_cache(self) -> None:
		"""测试清空所有缓存"""
		cache = OpenApiCache()
		cache.set('key1', 'value1')
		cache.set('key2', 'value2')
		cache.set('key3', 'value3')

		assert len(cache) == 3

		cache.clear()

		assert len(cache) == 0
		assert cache.get('key1') is None
		assert cache.get('key2') is None
		assert cache.get('key3') is None

	def test_cache_overwrites_existing_key(self) -> None:
		"""测试覆盖已存在的缓存项"""
		cache = OpenApiCache()
		cache.set('test_key', 'old_value')
		cache.set('test_key', 'new_value')

		result = cache.get('test_key')
		assert result == 'new_value'
		assert len(cache) == 1

	def test_cache_with_different_data_types(self) -> None:
		"""测试缓存不同的数据类型"""
		cache = OpenApiCache()

		# 字符串
		cache.set('str', 'hello')
		assert cache.get('str') == 'hello'

		# 整数
		cache.set('int', 42)
		assert cache.get('int') == 42

		# 列表
		cache.set('list', [1, 2, 3])
		assert cache.get('list') == [1, 2, 3]

		# 字典
		cache.set('dict', {'a': 1, 'b': 2})
		assert cache.get('dict') == {'a': 1, 'b': 2}

		# None 值
		cache.set('none', None)
		assert cache.get('none') is None

		# 布尔值
		cache.set('bool_true', True)
		cache.set('bool_false', False)
		assert cache.get('bool_true') is True
		assert cache.get('bool_false') is False

	def test_cache_contains_operator(self) -> None:
		"""测试 __contains__ 运算符"""
		cache = OpenApiCache()
		cache.set('existing', 'value')

		assert 'existing' in cache
		assert 'nonexistent' not in cache

	def test_cache_contains_expired_key(self) -> None:
		"""测试 __contains__ 对过期键的处理"""
		cache = OpenApiCache()
		cache.set('expired', 'value', ttl=1)

		# 立即检查，应该存在
		assert 'expired' in cache

		# 等待过期
		time.sleep(1.1)

		# 检查，应该不存在
		assert 'expired' not in cache

	def test_multiple_keys_with_different_ttl(self) -> None:
		"""测试多个键具有不同的 TTL"""
		cache = OpenApiCache()

		cache.set('short_ttl', 'value1', ttl=1)
		cache.set('long_ttl', 'value2', ttl=10)
		cache.set('no_ttl', 'value3')

		# 立即获取，都应该存在
		assert cache.get('short_ttl') == 'value1'
		assert cache.get('long_ttl') == 'value2'
		assert cache.get('no_ttl') == 'value3'

		# 等待短 TTL 过期
		time.sleep(1.1)

		# 短 TTL 已过期
		assert cache.get('short_ttl') is None
		# 长 TTL 和无 TTL 仍然存在
		assert cache.get('long_ttl') == 'value2'
		assert cache.get('no_ttl') == 'value3'

	def test_cache_len_includes_expired_entries(self) -> None:
		"""测试 __len__ 包含已过期但未清理的项"""
		cache = OpenApiCache()
		cache.set('key1', 'value1', ttl=1)

		assert len(cache) == 1

		# 等待过期，但不调用 get（不触发清理）
		time.sleep(1.1)

		# len 仍然包含过期项
		assert len(cache) == 1

		# 调用 get 触发清理
		cache.get('key1')
		assert len(cache) == 0

	def test_empty_string_key(self) -> None:
		"""测试空字符串作为键"""
		cache = OpenApiCache()
		cache.set('', 'value')

		assert cache.get('') == 'value'
		assert '' in cache

	def test_cache_with_complex_nested_data(self) -> None:
		"""测试缓存复杂的嵌套数据结构"""
		cache = OpenApiCache()
		complex_data = {
			'level1': {
				'level2': {
					'level3': ['a', 'b', 'c'],
					'number': 42,
				}
			},
			'list': [1, {'nested': True}, [3, 4]],
		}

		cache.set('complex', complex_data)
		result = cache.get('complex')

		assert result is not None
		assert result == complex_data
		assert result['level1']['level2']['level3'] == ['a', 'b', 'c']


class TestCacheStats:
	"""测试缓存统计信息"""

	def test_initial_stats(self) -> None:
		"""测试初始统计信息"""
		stats = CacheStats()

		assert stats.hits == 0
		assert stats.misses == 0
		assert stats.evictions == 0
		assert stats.total_sets == 0
		assert stats.total_gets == 0
		assert stats.hit_rate == 0.0

	def test_hit_rate_calculation(self) -> None:
		"""测试命中率计算"""
		stats = CacheStats()

		# 没有访问时
		assert stats.hit_rate == 0.0

		# 添加一些访问
		stats.hits = 8
		stats.misses = 2
		stats.total_gets = 10

		assert stats.hit_rate == 0.8

	def test_reset_stats(self) -> None:
		"""测试重置统计信息"""
		stats = CacheStats()
		stats.hits = 10
		stats.misses = 5
		stats.evictions = 2
		stats.total_sets = 15
		stats.total_gets = 15

		stats.reset()

		assert stats.hits == 0
		assert stats.misses == 0
		assert stats.evictions == 0
		assert stats.total_sets == 0
		assert stats.total_gets == 0


class TestLRUCache:
	"""测试 LRU 缓存"""

	def test_basic_operations(self) -> None:
		"""测试基本操作"""
		cache = LRUCache(max_size=3, default_ttl=60)

		# 设置和获取
		cache.set('key1', 'value1')
		assert cache.get('key1') == 'value1'
		assert 'key1' in cache
		assert len(cache) == 1

		# 不存在的键
		assert cache.get('nonexistent') is None
		assert 'nonexistent' not in cache

	def test_ttl_expiration(self) -> None:
		"""测试 TTL 过期"""
		cache = LRUCache(default_ttl=1)  # 1 秒 TTL

		cache.set('key1', 'value1')
		assert cache.get('key1') == 'value1'

		# 等待过期
		time.sleep(1.1)
		assert cache.get('key1') is None
		assert 'key1' not in cache

	def test_custom_ttl(self) -> None:
		"""测试自定义 TTL"""
		cache = LRUCache(default_ttl=60)

		# 使用自定义 TTL
		cache.set('key1', 'value1', ttl=1)
		time.sleep(1.1)
		assert cache.get('key1') is None

		# 使用默认 TTL
		cache.set('key2', 'value2')
		assert cache.get('key2') == 'value2'

	def test_lru_eviction(self) -> None:
		"""测试 LRU 驱逐"""
		cache = LRUCache(max_size=2)

		cache.set('key1', 'value1')
		cache.set('key2', 'value2')
		assert len(cache) == 2

		# 添加第三个键，应该驱逐最旧的
		cache.set('key3', 'value3')
		assert len(cache) == 2
		assert cache.get('key1') is None  # 应该被驱逐
		assert cache.get('key2') == 'value2'
		assert cache.get('key3') == 'value3'

	def test_lru_update(self) -> None:
		"""测试 LRU 更新顺序"""
		cache = LRUCache(max_size=2)

		cache.set('key1', 'value1')
		cache.set('key2', 'value2')

		# 访问 key1，使其成为最近使用的
		cache.get('key1')

		# 添加新键，应该驱逐 key2（不是 key1）
		cache.set('key3', 'value3')
		assert cache.get('key1') == 'value1'  # 仍然存在
		assert cache.get('key2') is None      # 被驱逐
		assert cache.get('key3') == 'value3'

	def test_stats(self) -> None:
		"""测试统计信息"""
		cache = LRUCache(max_size=10)

		stats = cache.get_stats()
		assert stats['hits'] == 0
		assert stats['misses'] == 0
		assert stats['hit_rate'] == 0.0
		assert stats['evictions'] == 0
		assert stats['total_sets'] == 0
		assert stats['total_gets'] == 0
		assert stats['size'] == 0

		# 添加一些操作
		cache.set('key1', 'value1')
		cache.get('key1')  # 命中
		cache.get('nonexistent')  # 未命中

		stats = cache.get_stats()
		assert stats['hits'] == 1
		assert stats['misses'] == 1
		assert stats['hit_rate'] == 0.5
		assert stats['total_sets'] == 1
		assert stats['total_gets'] == 2
		assert stats['size'] == 1

	def test_cleanup_expired(self) -> None:
		"""测试清理过期条目"""
		cache = LRUCache(default_ttl=1)

		cache.set('key1', 'value1')
		cache.set('key2', 'value2')

		assert len(cache) == 2

		# 等待过期
		time.sleep(1.1)

		cleaned = cache.cleanup_expired()
		assert cleaned == 2
		assert len(cache) == 0

	def test_clear_and_invalidate(self) -> None:
		"""测试清空和失效"""
		cache = LRUCache()

		cache.set('key1', 'value1')
		cache.set('key2', 'value2')

		# 失效单个键
		assert cache.invalidate('key1') is True
		assert cache.get('key1') is None
		assert cache.get('key2') == 'value2'

		# 失效不存在的键
		assert cache.invalidate('nonexistent') is False

		# 清空所有
		cache.clear()
		assert len(cache) == 0
		assert cache.get_stats()['hits'] == 0

	def test_invalid_parameters(self) -> None:
		"""测试无效参数"""
		with pytest.raises(ValueError):
			LRUCache(max_size=0)

		cache = LRUCache()
		with pytest.raises(ValueError):
			cache.set('key1', 'value1', ttl=-1)


class TestMultiLevelCache:
	"""测试多级缓存"""

	def test_basic_operations(self) -> None:
		"""测试基本操作"""
		cache = MultiLevelCache(l1_size=2, l2_size=4)

		cache.set('key1', 'value1')
		assert cache.get('key1') == 'value1'

		# 数据应该在 L1 和 L2 中
		assert 'key1' in cache.l1_cache
		assert 'key1' in cache.l2_cache

	def test_l1_miss_l2_hit(self) -> None:
		"""测试 L1 未命中但 L2 命中"""
		cache = MultiLevelCache(l1_size=1, l2_size=10)

		# 在 L2 中设置数据
		cache.l2_cache.set('key2', 'value2')

		# 访问 key2，应该从 L2 提升到 L1
		assert cache.get('key2') == 'value2'
		assert 'key2' in cache.l1_cache

	def test_disable_l2(self) -> None:
		"""测试禁用 L2 缓存"""
		cache = MultiLevelCache(l1_size=10, enable_l2=False)

		assert cache.l2_cache is None

		cache.set('key1', 'value1')
		assert cache.get('key1') == 'value1'

		# 数据应该只在 L1 中
		assert 'key1' in cache.l1_cache

	def test_stats(self) -> None:
		"""测试统计信息"""
		cache = MultiLevelCache(l1_size=10, l2_size=10)

		cache.set('key1', 'value1')
		cache.get('key1')  # 命中
		cache.get('nonexistent')  # 未命中

		stats = cache.get_stats()

		assert 'l1_cache' in stats
		assert 'l2_cache' in stats
		assert 'total_hits' in stats
		assert 'total_misses' in stats
		assert 'overall_hit_rate' in stats

		assert stats['total_hits'] == 1
		assert stats['total_misses'] == 1
		assert stats['overall_hit_rate'] == 0.5

	def test_invalidate_and_clear(self) -> None:
		"""测试失效和清空"""
		cache = MultiLevelCache()

		cache.set('key1', 'value1')
		cache.set('key2', 'value2')

		# 失效单个键
		assert cache.invalidate('key1') is True
		assert cache.get('key1') is None
		assert cache.get('key2') == 'value2'

		# 清空所有
		cache.clear()
		assert cache.get('key1') is None
		assert cache.get('key2') is None


class TestResourceCache:
	"""测试 Resource 缓存"""

	def test_spec_caching(self) -> None:
		"""测试 OpenAPI spec 缓存"""
		cache = ResourceCache()

		spec = {'openapi': '3.0.0', 'info': {'title': 'Test API'}}
		cache.set_spec(spec)

		cached_spec = cache.get_spec()
		assert cached_spec == spec
		assert cached_spec is not spec  # 应该是不同的对象

	def test_endpoints_caching(self) -> None:
		"""测试端点缓存"""
		cache = ResourceCache()

		endpoints = [
			{'path': '/users', 'method': 'GET'},
			{'path': '/users', 'method': 'POST'}
		]
		cache.set_endpoints(endpoints)

		cached_endpoints = cache.get_endpoints()
		assert cached_endpoints == endpoints

	def test_model_caching(self) -> None:
		"""测试模型缓存"""
		cache = ResourceCache()

		model_def = {
			'type': 'object',
			'properties': {'id': {'type': 'integer'}}
		}
		cache.set_model('User', model_def)

		cached_model = cache.get_model('User')
		assert cached_model == model_def
		assert cache.get_model('NonExistent') is None

	def test_tag_endpoints_caching(self) -> None:
		"""测试标签端点缓存"""
		cache = ResourceCache()

		tag_endpoints = [
			{'path': '/users', 'method': 'GET'},
			{'path': '/users/{id}', 'method': 'GET'}
		]
		cache.set_tag_endpoints('user', tag_endpoints)

		cached_endpoints = cache.get_tag_endpoints('user')
		assert cached_endpoints == tag_endpoints
		assert cache.get_tag_endpoints('nonexistent') is None

	def test_different_ttl_values(self) -> None:
		"""测试不同的 TTL 值"""
		cache = ResourceCache(
			spec_ttl=1,
			endpoints_ttl=2,
			models_ttl=3,
			tags_ttl=4
		)

		# 设置所有类型的缓存
		cache.set_spec({'openapi': '3.0.0'})
		cache.set_endpoints([{'path': '/test'}])
		cache.set_model('Test', {'type': 'object'})
		cache.set_tag_endpoints('test', [{'path': '/test'}])

		# 验证都存在
		assert cache.get_spec() is not None
		assert cache.get_endpoints() is not None
		assert cache.get_model('Test') is not None
		assert cache.get_tag_endpoints('test') is not None

		# 等待 spec 过期
		time.sleep(1.1)
		assert cache.get_spec() is None
		assert cache.get_endpoints() is not None
		assert cache.get_model('Test') is not None
		assert cache.get_tag_endpoints('test') is not None

	def test_clear_and_stats(self) -> None:
		"""测试清空和统计"""
		cache = ResourceCache()

		cache.set_spec({'openapi': '3.0.0'})
		cache.set_endpoints([{'path': '/test'}])

		stats = cache.get_stats()
		assert stats['size'] > 0

		cache.clear()
		assert cache.get_spec() is None
		assert cache.get_endpoints() is None
		assert cache.get_stats()['size'] == 0

	def test_invalidate_by_type(self) -> None:
		"""测试按类型失效"""
		cache = ResourceCache()

		cache.set_spec({'openapi': '3.0.0'})
		cache.set_endpoints([{'path': '/test'}])

		# 由于使用哈希键，按类型失效会清空所有缓存
		invalidated = cache.invalidate_by_type('spec')
		assert cache.get_spec() is None
		assert cache.get_endpoints() is None
