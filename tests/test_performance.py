"""
测试性能监控功能
"""

import time
from unittest.mock import Mock

import pytest

from openapi_mcp.performance import (
	CacheStats,
	PerformanceMetrics,
	PerformanceMonitor,
	SlidingWindowMetrics,
	get_global_monitor,
	measure,
)


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


class TestPerformanceMetrics:
	"""测试性能指标"""

	def test_initial_metrics(self) -> None:
		"""测试初始指标"""
		metrics = PerformanceMetrics()

		assert metrics.total_calls == 0
		assert metrics.total_duration == 0.0
		assert metrics.min_duration == float('inf')
		assert metrics.max_duration == 0.0
		assert metrics.errors == 0
		assert metrics.last_call_time is None
		assert metrics.avg_duration == 0.0
		assert metrics.error_rate == 0.0

	def test_update_metrics(self) -> None:
		"""测试更新指标"""
		metrics = PerformanceMetrics()

		# 添加成功的调用
		metrics.update(0.1, True)
		assert metrics.total_calls == 1
		assert metrics.total_duration == 0.1
		assert metrics.min_duration == 0.1
		assert metrics.max_duration == 0.1
		assert metrics.avg_duration == 0.1
		assert metrics.error_rate == 0.0
		assert metrics.last_call_time is not None

		# 添加另一个调用
		metrics.update(0.2, True)
		assert metrics.total_calls == 2
		assert metrics.total_duration == 0.3
		assert metrics.min_duration == 0.1
		assert metrics.max_duration == 0.2
		assert metrics.avg_duration == 0.15

		# 添加失败的调用
		metrics.update(0.05, False)
		assert metrics.total_calls == 3
		assert metrics.total_duration == 0.35
		assert metrics.min_duration == 0.05
		assert metrics.max_duration == 0.2
		assert metrics.errors == 1
		assert metrics.error_rate == 1.0 / 3.0


class TestSlidingWindowMetrics:
	"""测试滑动窗口指标"""

	def test_initial_metrics(self) -> None:
		"""测试初始指标"""
		window = SlidingWindowMetrics()

		metrics = window.get_metrics()
		assert metrics['calls_per_second'] == 0.0
		assert metrics['avg_duration'] == 0.0
		assert metrics['p95_duration'] == 0.0
		assert metrics['p99_duration'] == 0.0
		assert metrics['error_rate'] == 0.0
		assert metrics['total_calls'] == 0

	def test_add_and_get_metrics(self) -> None:
		"""测试添加和获取指标"""
		window = SlidingWindowMetrics()

		# 添加一些调用
		now = time.time()
		window.add(0.1, True)
		window.add(0.2, True)
		window.add(0.3, False)

		metrics = window.get_metrics(60.0)

		assert metrics['total_calls'] == 3
		assert metrics['calls_per_second'] == pytest.approx(3.0 / 60.0)
		assert metrics['avg_duration'] == pytest.approx(0.2)
		assert metrics['error_rate'] == pytest.approx(1.0 / 3.0)

		# 验证百分位数
		sorted_durations = [0.1, 0.2, 0.3]
		p95_idx = int(0.95 * 3)  # 2
		p99_idx = int(0.99 * 3)  # 2

		assert metrics['p95_duration'] == sorted_durations[p95_idx]
		assert metrics['p99_duration'] == sorted_durations[p99_idx]

	def test_window_size_limit(self) -> None:
		"""测试窗口大小限制"""
		window = SlidingWindowMetrics(window_size=2)

		# 添加超过窗口大小的调用
		window.add(0.1, True)
		window.add(0.2, True)
		window.add(0.3, True)  # 这会移除最旧的调用

		assert len(window.calls) == 2
		assert len(window.durations) == 2
		assert len(window.errors) == 2


class TestPerformanceMonitor:
	"""测试性能监控器"""

	def test_initial_monitor(self) -> None:
		"""测试初始监控器"""
		monitor = PerformanceMonitor()

		assert monitor.is_enabled()
		assert monitor.get_all_metrics() == {}

	def test_record_operation(self) -> None:
		"""测试记录操作"""
		monitor = PerformanceMonitor()

		# 记录一些操作
		monitor.record_operation('test_op', 0.1, True)
		monitor.record_operation('test_op', 0.2, True)
		monitor.record_operation('test_op', 0.3, False)

		metrics = monitor.get_metrics('test_op')

		assert metrics['total_calls'] == 3
		assert metrics['avg_duration'] == pytest.approx(0.2)
		assert metrics['error_rate'] == pytest.approx(1.0 / 3.0)
		assert metrics['min_duration'] == 0.1
		assert metrics['max_duration'] == 0.3

	def test_disable_monitor(self) -> None:
		"""测试禁用监控器"""
		monitor = PerformanceMonitor()

		monitor.disable()
		assert not monitor.is_enabled()

		# 禁用时不记录操作
		monitor.record_operation('test_op', 0.1, True)
		assert monitor.get_metrics('test_op') == {}

		monitor.enable()
		assert monitor.is_enabled()

	def test_measure_context_manager(self) -> None:
		"""测试性能测量上下文管理器"""
		monitor = PerformanceMonitor()

		with monitor.measure('test_operation'):
			time.sleep(0.01)  # 模拟耗时操作

		metrics = monitor.get_metrics('test_operation')
		assert metrics['total_calls'] == 1
		assert metrics['avg_duration'] > 0.01
		assert metrics['error_rate'] == 0.0

	def test_measure_context_manager_with_error(self) -> None:
		"""测试性能测量上下文管理器处理错误"""
		monitor = PerformanceMonitor()

		with pytest.raises(ValueError):
			with monitor.measure('test_operation'):
				raise ValueError("Test error")

		metrics = monitor.get_metrics('test_operation')
		assert metrics['total_calls'] == 1
		assert metrics['error_rate'] == 1.0
		assert metrics['errors'] == 1

	def test_decorator_sync_function(self) -> None:
		"""测试同步函数装饰器"""
		monitor = PerformanceMonitor()

		@monitor.decorate('decorated_func')
		def test_function(x: int) -> int:
			time.sleep(0.01)
			return x * 2

		result = test_function(5)
		assert result == 10

		metrics = monitor.get_metrics('decorated_func')
		assert metrics['total_calls'] == 1
		assert metrics['avg_duration'] > 0.01
		assert metrics['error_rate'] == 0.0

	@pytest.mark.asyncio
	async def test_decorator_async_function(self) -> None:
		"""测试异步函数装饰器"""
		monitor = PerformanceMonitor()

		@monitor.decorate('async_func')
		async def async_test_function(x: int) -> int:
			await asyncio.sleep(0.01)
			return x * 3

		result = await async_test_function(5)
		assert result == 15

		metrics = monitor.get_metrics('async_func')
		assert metrics['total_calls'] == 1
		assert metrics['avg_duration'] > 0.01
		assert metrics['error_rate'] == 0.0

	def test_slow_operations(self) -> None:
		"""测试获取慢操作"""
		monitor = PerformanceMonitor()

		# 添加不同耗时的操作
		monitor.record_operation('fast_op', 0.05, True)
		monitor.record_operation('slow_op', 1.5, True)
		monitor.record_operation('very_slow_op', 2.0, True)

		slow_ops = monitor.get_slow_operations(threshold=1.0)
		assert len(slow_ops) == 2

		# 验证按耗时排序
		assert slow_ops[0]['operation'] == 'very_slow_op'
		assert slow_ops[0]['avg_duration'] == 2.0
		assert slow_ops[1]['operation'] == 'slow_op'
		assert slow_ops[1]['avg_duration'] == 1.5

	def test_error_prone_operations(self) -> None:
		"""测试获取错误率高的操作"""
		monitor = PerformanceMonitor()

		# 添加不同错误率的操作
		for _ in range(10):
			monitor.record_operation('stable_op', 0.1, True)
			monitor.record_operation('unstable_op', 0.1, False)
		for _ in range(5):
			monitor.record_operation('unstable_op', 0.1, True)

		error_prone = monitor.get_error_prone_operations(threshold=0.1)
		assert len(error_prone) == 1
		assert error_prone[0]['operation'] == 'unstable_op'
		assert error_prone[0]['error_rate'] == 10.0 / 15.0

	def test_reset_metrics(self) -> None:
		"""测试重置指标"""
		monitor = PerformanceMonitor()

		monitor.record_operation('test_op', 0.1, True)
		monitor.record_operation('other_op', 0.2, True)

		assert len(monitor.get_all_metrics()) == 2

		# 重置单个操作
		monitor.reset_metrics('test_op')
		assert 'test_op' not in monitor.get_metrics('test_op')
		assert 'other_op' in monitor.get_metrics('other_op')

		# 重置所有操作
		monitor.reset_metrics()
		assert monitor.get_all_metrics() == {}

	def test_max_tracked_operations(self) -> None:
		"""测试最大跟踪操作数量"""
		monitor = PerformanceMonitor(max_tracked_operations=2)

		# 添加超过限制的操作
		monitor.record_operation('op1', 0.1, True)
		monitor.record_operation('op2', 0.1, True)
		monitor.record_operation('op3', 0.1, True)

		# 应该只保留最新的 2 个操作
		assert len(monitor.get_all_metrics()) <= 2


class TestGlobalMonitor:
	"""测试全局监控器"""

	def test_global_monitor_functions(self) -> None:
		"""测试全局监控器函数"""
		# 使用全局装饰器
		@measure('global_test_func')
		def test_func() -> int:
			time.sleep(0.01)
			return 42

		result = test_func()
		assert result == 42

		# 检查全局指标
		metrics = get_metrics('global_test_func')
		assert metrics['total_calls'] == 1
		assert metrics['avg_duration'] > 0.01

		# 获取所有指标
		all_metrics = get_all_metrics()
		assert 'global_test_func' in all_metrics

	def test_get_global_monitor(self) -> None:
		"""测试获取全局监控器"""
		monitor = get_global_monitor()
		assert isinstance(monitor, PerformanceMonitor)
		assert monitor.is_enabled()