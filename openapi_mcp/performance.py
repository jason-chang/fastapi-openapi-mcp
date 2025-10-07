"""
性能监控模块

提供性能指标收集、监控和分析功能。
"""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
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

	def record_hit(self) -> None:
		"""记录缓存命中"""
		self.hits += 1
		self.total_gets += 1

	def record_miss(self) -> None:
		"""记录缓存未命中"""
		self.misses += 1
		self.total_gets += 1

	def record_set(self) -> None:
		"""记录缓存设置"""
		self.total_sets += 1

	def record_eviction(self) -> None:
		"""记录缓存驱逐"""
		self.evictions += 1

	def reset(self) -> None:
		"""重置统计信息"""
		self.hits = 0
		self.misses = 0
		self.evictions = 0
		self.total_sets = 0
		self.total_gets = 0


@dataclass
class PerformanceMetrics:
	"""性能指标数据"""

	total_calls: int = 0
	total_duration: float = 0.0
	min_duration: float = float('inf')
	max_duration: float = 0.0
	errors: int = 0
	last_call_time: float | None = None

	@property
	def avg_duration(self) -> float:
		"""平均耗时"""
		return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0

	@property
	def error_rate(self) -> float:
		"""错误率"""
		return self.errors / self.total_calls if self.total_calls > 0 else 0.0

	def update(self, duration: float, success: bool = True) -> None:
		"""更新指标"""
		self.total_calls += 1
		self.total_duration += duration
		self.min_duration = min(self.min_duration, duration)
		self.max_duration = max(self.max_duration, duration)
		if not success:
			self.errors += 1
		self.last_call_time = time.time()


@dataclass
class SlidingWindowMetrics:
	"""滑动窗口性能指标"""

	window_size: int = 1000
	calls: deque = field(default_factory=lambda: deque(maxlen=1000))
	durations: deque = field(default_factory=lambda: deque(maxlen=1000))
	errors: deque = field(default_factory=lambda: deque(maxlen=1000))

	def add(self, duration: float, success: bool = True) -> None:
		"""添加新的调用记录"""
		timestamp = time.time()
		self.calls.append(timestamp)
		self.durations.append(duration)
		self.errors.append(0 if success else 1)

	def get_metrics(self, time_window: float = 60.0) -> dict[str, Any]:
		"""获取指定时间窗口内的指标"""
		now = time.time()
		cutoff = now - time_window

		# 过滤时间窗口内的数据
		recent_calls = [
			(t, d, e)
			for t, d, e in zip(self.calls, self.durations, self.errors, strict=False)
			if t >= cutoff
		]

		if not recent_calls:
			return {
				'calls_per_second': 0.0,
				'avg_duration': 0.0,
				'p95_duration': 0.0,
				'p99_duration': 0.0,
				'error_rate': 0.0,
				'total_calls': 0,
			}

		durations = [d for _, d, _ in recent_calls]
		errors = [e for _, _, e in recent_calls]

		# 计算百分位数
		sorted_durations = sorted(durations)
		_calls = len(recent_calls)

		p95_idx = int(0.95 * _calls)
		p99_idx = int(0.99 * _calls)

		return {
			'calls_per_second': _calls / time_window,
			'avg_duration': sum(durations) / _calls,
			'p95_duration': sorted_durations[p95_idx] if p95_idx < _calls else 0.0,
			'p99_duration': sorted_durations[p99_idx] if p99_idx < _calls else 0.0,
			'error_rate': sum(errors) / _calls,
			'total_calls': _calls,
		}


class PerformanceMonitor:
	"""性能监控器

	跟踪和分析各种操作的性能指标。
	"""

	def __init__(self, max_tracked_operations: int = 100) -> None:
		"""初始化性能监控器

		Args:
			max_tracked_operations: 最大跟踪的操作数量
		"""
		self._metrics: dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
		self._sliding_metrics: dict[str, SlidingWindowMetrics] = {}
		self.max_tracked_operations = max_tracked_operations
		self._enabled = True

	def enable(self) -> None:
		"""启用性能监控"""
		self._enabled = True
		logger.info('Performance monitoring enabled')

	def disable(self) -> None:
		"""禁用性能监控"""
		self._enabled = False
		logger.info('Performance monitoring disabled')

	def is_enabled(self) -> bool:
		"""检查是否启用"""
		return self._enabled

	def record_operation(
		self, operation_name: str, duration: float, success: bool = True
	) -> None:
		"""记录操作性能

		Args:
			operation_name: 操作名称
			duration: 耗时（秒）
			success: 是否成功
		"""
		if not self._enabled:
			return

		# 更新基本指标
		self._metrics[operation_name].update(duration, success)

		# 更新滑动窗口指标
		if operation_name not in self._sliding_metrics:
			self._sliding_metrics[operation_name] = SlidingWindowMetrics()

		self._sliding_metrics[operation_name].add(duration, success)

		# 限制跟踪的操作数量
		if len(self._metrics) > self.max_tracked_operations:
			# 移除最少使用的操作
			oldest_op = min(
				self._metrics.items(), key=lambda x: x[1].last_call_time or float('inf')
			)[0]
			del self._metrics[oldest_op]
			if oldest_op in self._sliding_metrics:
				del self._sliding_metrics[oldest_op]

	def get_metrics(self, operation_name: str) -> dict[str, Any]:
		"""获取指定操作的性能指标

		Args:
			operation_name: 操作名称

		Returns:
			性能指标字典
		"""
		if operation_name not in self._metrics:
			return {}

		basic_metrics = self._metrics[operation_name]
		sliding_metrics = self._sliding_metrics.get(operation_name)

		result = {
			'operation': operation_name,
			'total_calls': basic_metrics.total_calls,
			'avg_duration': basic_metrics.avg_duration,
			'min_duration': basic_metrics.min_duration,
			'max_duration': basic_metrics.max_duration,
			'error_rate': basic_metrics.error_rate,
			'errors': basic_metrics.errors,
			'last_call_time': basic_metrics.last_call_time,
		}

		if sliding_metrics:
			# 添加最近 1 分钟的指标
			recent_1m = sliding_metrics.get_metrics(60.0)
			result.update(
				{
					'recent_1m_calls_per_second': recent_1m['calls_per_second'],
					'recent_1m_avg_duration': recent_1m['avg_duration'],
					'recent_1m_p95_duration': recent_1m['p95_duration'],
					'recent_1m_p99_duration': recent_1m['p99_duration'],
					'recent_1m_error_rate': recent_1m['error_rate'],
					'recent_1m_total_calls': recent_1m['total_calls'],
				}
			)

			# 添加最近 5 分钟的指标
			recent_5m = sliding_metrics.get_metrics(300.0)
			result.update(
				{
					'recent_5m_calls_per_second': recent_5m['calls_per_second'],
					'recent_5m_avg_duration': recent_5m['avg_duration'],
					'recent_5m_error_rate': recent_5m['error_rate'],
				}
			)

		return result

	def get_all_metrics(self) -> dict[str, dict[str, Any]]:
		"""获取所有操作的性能指标

		Returns:
			所有性能指标字典
		"""
		return {op: self.get_metrics(op) for op in self._metrics.keys()}

	def get_slow_operations(
		self, threshold: float = 1.0, limit: int = 10
	) -> list[dict[str, Any]]:
		"""获取慢操作列表

		Args:
			threshold: 慢操作阈值（秒）
			limit: 返回数量限制

		Returns:
			慢操作列表
		"""
		slow_ops = []

		for op_name, metrics in self._metrics.items():
			if metrics.avg_duration >= threshold:
				slow_ops.append(
					{
						'operation': op_name,
						'avg_duration': metrics.avg_duration,
						'max_duration': metrics.max_duration,
						'total_calls': metrics.total_calls,
						'error_rate': metrics.error_rate,
					}
				)

		# 按平均耗时排序
		slow_ops.sort(key=lambda x: x['avg_duration'], reverse=True)
		return slow_ops[:limit]

	def get_error_prone_operations(
		self, error_rate_threshold: float = 0.1, limit: int = 10
	) -> list[dict[str, Any]]:
		"""获取错误率高的操作

		Args:
			error_rate_threshold: 错误率阈值
			limit: 返回数量限制

		Returns:
			错误率高的操作列表
		"""
		error_prone = []

		for op_name, metrics in self._metrics.items():
			if metrics.error_rate >= error_rate_threshold and metrics.total_calls >= 10:
				error_prone.append(
					{
						'operation': op_name,
						'error_rate': metrics.error_rate,
						'total_calls': metrics.total_calls,
						'errors': metrics.errors,
						'avg_duration': metrics.avg_duration,
					}
				)

		# 按错误率排序
		error_prone.sort(key=lambda x: x['error_rate'], reverse=True)
		return error_prone[:limit]

	def reset_metrics(self, operation_name: str | None = None) -> None:
		"""重置性能指标

		Args:
			operation_name: 操作名称，None 表示重置所有
		"""
		if operation_name:
			if operation_name in self._metrics:
				del self._metrics[operation_name]
			if operation_name in self._sliding_metrics:
				del self._sliding_metrics[operation_name]
		else:
			self._metrics.clear()
			self._sliding_metrics.clear()

	@contextmanager
	def measure(self, operation_name: str):
		"""性能测量上下文管理器

		Args:
			operation_name: 操作名称

		Example:
			>>> monitor = PerformanceMonitor()
			>>> with monitor.measure('database_query'):
			...     # 执行数据库查询
			...     result = db.execute("SELECT * FROM users")
		"""
		if not self._enabled:
			yield
			return

		start_time = time.time()
		success = True

		try:
			yield
		except Exception as e:
			success = False
			logger.warning(f'Operation {operation_name} failed: {e}')
			raise
		finally:
			duration = time.time() - start_time
			self.record_operation(operation_name, duration, success)

	def decorate(self, operation_name: str | None = None) -> Callable:
		"""性能监控装饰器

		Args:
			operation_name: 操作名称，None 使用函数名

		Example:
			>>> monitor = PerformanceMonitor()
			>>> @monitor.decorate('api_call')
			... def fetch_user(user_id):
			...     # API 调用逻辑
			...     return api.get_user(user_id)
		"""

		def decorator(func: Callable) -> Callable:
			op_name = operation_name or f'{func.__module__}.{func.__name__}'

			@wraps(func)
			def sync_wrapper(*args, **kwargs):
				if not self._enabled:
					return func(*args, **kwargs)

				start_time = time.time()
				success = True

				try:
					result = func(*args, **kwargs)
					return result
				except Exception as e:
					success = False
					logger.warning(f'Operation {op_name} failed: {e}')
					raise
				finally:
					duration = time.time() - start_time
					self.record_operation(op_name, duration, success)

			@wraps(func)
			async def async_wrapper(*args, **kwargs):
				if not self._enabled:
					return await func(*args, **kwargs)

				start_time = time.time()
				success = True

				try:
					result = await func(*args, **kwargs)
					return result
				except Exception as e:
					success = False
					logger.warning(f'Operation {op_name} failed: {e}')
					raise
				finally:
					duration = time.time() - start_time
					self.record_operation(op_name, duration, success)

			# 根据函数类型返回合适的包装器
			import asyncio

			if asyncio.iscoroutinefunction(func):
				return async_wrapper
			else:
				return sync_wrapper

		return decorator


# 全局性能监控器实例
_global_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
	"""获取全局性能监控器

	Returns:
		全局性能监控器实例
	"""
	return _global_monitor


def measure(operation_name: str):
	"""全局性能测量装饰器

	Args:
		operation_name: 操作名称
	"""
	return _global_monitor.decorate(operation_name)


def get_metrics(operation_name: str) -> dict[str, Any]:
	"""获取全局性能指标

	Args:
		operation_name: 操作名称

	Returns:
		性能指标字典
	"""
	return _global_monitor.get_metrics(operation_name)


def get_all_metrics() -> dict[str, dict[str, Any]]:
	"""获取所有全局性能指标

	Returns:
		所有性能指标字典
	"""
	return _global_monitor.get_all_metrics()
