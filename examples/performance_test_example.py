"""
性能测试示例

展示如何对 OpenAPI MCP Server 进行性能测试和基准测试。
包括负载测试、并发测试、内存使用测试等。
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median
from typing import Any

import aiohttp
import psutil
from fastapi import FastAPI
from openapi_mcp.client import OpenApiMcpClient
from openapi_mcp.transport.http import HttpMcpTransport

from openapi_mcp import OpenApiMcpServer


# 创建性能测试用的应用
def create_performance_test_app() -> FastAPI:
	"""创建性能测试应用"""
	app = FastAPI(
		title='Performance Test API',
		version='1.0.0',
		description='用于性能测试的 API',
	)

	# 简单的端点
	@app.get('/simple')
	async def simple_endpoint():
		"""简单端点 - 快速响应"""
		return {'message': 'Hello World', 'timestamp': time.time()}

	# 中等复杂度端点
	@app.get('/medium')
	async def medium_endpoint():
		"""中等复杂度端点 - 需要一些计算"""
		# 模拟一些计算
		result = sum(i * i for i in range(100))
		return {'result': result, 'timestamp': time.time()}

	# 复杂端点
	@app.get('/complex')
	async def complex_endpoint():
		"""复杂端点 - 大量数据处理"""
		# 模拟复杂计算
		data = []
		for i in range(1000):
			item = {
				'id': i,
				'name': f'item_{i}',
				'value': i * 2,
				'metadata': {
					'created': time.time(),
					'tags': [f'tag_{j}' for j in range(5)],
				},
			}
			data.append(item)
		return {'data': data, 'total': len(data)}

	# 带参数的端点
	@app.get('/params/{item_id}')
	async def params_endpoint(item_id: int, query: str = ''):
		"""带参数端点"""
		return {'item_id': item_id, 'query': query, 'timestamp': time.time()}

	# 返回大量数据的端点
	@app.get('/large-data')
	async def large_data_endpoint():
		"""返回大量数据的端点"""
		data = []
		for i in range(5000):
			data.append(
				{
					'id': i,
					'content': 'x' * 100,  # 100字符的内容
					'metadata': {'index': i, 'hash': hash(f'item_{i}')},
				}
			)
		return {'data': data, 'size': len(data)}

	return app


@dataclass
class PerformanceMetrics:
	"""性能指标数据类"""

	endpoint: str
	total_requests: int
	successful_requests: int
	failed_requests: int
	avg_response_time: float
	min_response_time: float
	max_response_time: float
	median_response_time: float
	p95_response_time: float
	p99_response_time: float
	requests_per_second: float
	error_rate: float
	total_duration: float


@dataclass
class SystemMetrics:
	"""系统指标数据类"""

	cpu_percent: float
	memory_percent: float
	memory_used_mb: float
	memory_available_mb: float
	disk_io_read_mb: float
	disk_io_write_mb: float
	network_io_sent_mb: float
	network_io_recv_mb: float


class PerformanceTester:
	"""性能测试器"""

	def __init__(self, base_url: str = 'http://localhost:8000'):
		self.base_url = base_url
		self.mcp_url = f'{base_url}/mcp'
		self.session: aiohttp.ClientSession | None = None

	async def __aenter__(self):
		"""异步上下文管理器入口"""
		self.session = aiohttp.ClientSession()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""异步上下文管理器出口"""
		if self.session:
			await self.session.close()

	async def test_endpoint_performance(
		self,
		endpoint: str,
		concurrent_users: int = 10,
		requests_per_user: int = 50,
		duration_seconds: int | None = None,
	) -> PerformanceMetrics:
		"""测试单个端点的性能"""
		print(f'\n🚀 测试端点: {endpoint}')
		print(f'   并发用户: {concurrent_users}, 每用户请求数: {requests_per_user}')

		url = f'{self.base_url}{endpoint}'
		response_times = []
		successful_requests = 0
		failed_requests = 0
		start_time = time.time()

		# 创建并发任务
		async def user_session():
			nonlocal successful_requests, failed_requests
			user_response_times = []

			for _i in range(requests_per_user):
				request_start = time.time()
				try:
					async with self.session.get(url) as response:
						if response.status == 200:
							await response.text()  # 读取响应内容
							successful_requests += 1
						else:
							failed_requests += 1
				except Exception:
					failed_requests += 1

				request_time = time.time() - request_start
				user_response_times.append(request_time)

				# 检查是否超时
				if duration_seconds and (time.time() - start_time) > duration_seconds:
					break

			return user_response_times

		# 执行并发测试
		tasks = [user_session() for _ in range(concurrent_users)]
		results = await asyncio.gather(*tasks)

		# 收集所有响应时间
		for user_times in results:
			response_times.extend(user_times)

		total_duration = time.time() - start_time
		total_requests = successful_requests + failed_requests

		# 计算指标
		if response_times:
			avg_response_time = mean(response_times)
			min_response_time = min(response_times)
			max_response_time = max(response_times)
			median_response_time = median(response_times)

			# 计算百分位数
			sorted_times = sorted(response_times)
			p95_index = int(len(sorted_times) * 0.95)
			p99_index = int(len(sorted_times) * 0.99)
			p95_response_time = (
				sorted_times[p95_index]
				if p95_index < len(sorted_times)
				else max_response_time
			)
			p99_response_time = (
				sorted_times[p99_index]
				if p99_index < len(sorted_times)
				else max_response_time
			)
		else:
			avg_response_time = min_response_time = max_response_time = 0
			median_response_time = p95_response_time = p99_response_time = 0

		requests_per_second = (
			total_requests / total_duration if total_duration > 0 else 0
		)
		error_rate = (
			(failed_requests / total_requests * 100) if total_requests > 0 else 0
		)

		metrics = PerformanceMetrics(
			endpoint=endpoint,
			total_requests=total_requests,
			successful_requests=successful_requests,
			failed_requests=failed_requests,
			avg_response_time=avg_response_time * 1000,  # 转换为毫秒
			min_response_time=min_response_time * 1000,
			max_response_time=max_response_time * 1000,
			median_response_time=median_response_time * 1000,
			p95_response_time=p95_response_time * 1000,
			p99_response_time=p99_response_time * 1000,
			requests_per_second=requests_per_second,
			error_rate=error_rate,
			total_duration=total_duration,
		)

		return metrics

	async def test_mcp_performance(
		self, tool_name: str, concurrent_users: int = 5, requests_per_user: int = 20
	) -> PerformanceMetrics:
		"""测试 MCP 工具的性能"""
		print(f'\n🔧 测试 MCP 工具: {tool_name}')

		async def mcp_request():
			"""执行 MCP 请求"""
			start_time = time.time()
			try:
				transport = HttpMcpTransport(self.mcp_url)
				client = OpenApiMcpClient(transport)
				await transport.connect()

				# 调用工具
				if tool_name == 'search_endpoints':
					await client.call_tool(tool_name, {'query': 'test'})
				elif tool_name == 'generate_examples':
					await client.call_tool(
						tool_name, {'endpoint_path': '/test', 'method': 'GET'}
					)
				else:
					await client.call_tool(tool_name, {})

				await transport.disconnect()
				return True, time.time() - start_time

			except Exception as e:
				print(f'    MCP 请求失败: {e}')
				return False, time.time() - start_time

		# 执行并发测试
		response_times = []
		successful_requests = 0
		failed_requests = 0
		start_time = time.time()

		async def user_session():
			nonlocal successful_requests, failed_requests
			user_response_times = []

			for _ in range(requests_per_user):
				success, request_time = await mcp_request()
				user_response_times.append(request_time)

				if success:
					successful_requests += 1
				else:
					failed_requests += 1

			return user_response_times

		tasks = [user_session() for _ in range(concurrent_users)]
		results = await asyncio.gather(*tasks)

		for user_times in results:
			response_times.extend(user_times)

		total_duration = time.time() - start_time
		total_requests = successful_requests + failed_requests

		# 计算指标（同上）
		if response_times:
			avg_response_time = mean(response_times)
			min_response_time = min(response_times)
			max_response_time = max(response_times)
			median_response_time = median(response_times)

			sorted_times = sorted(response_times)
			p95_index = int(len(sorted_times) * 0.95)
			p99_index = int(len(sorted_times) * 0.99)
			p95_response_time = (
				sorted_times[p95_index]
				if p95_index < len(sorted_times)
				else max_response_time
			)
			p99_response_time = (
				sorted_times[p99_index]
				if p99_index < len(sorted_times)
				else max_response_time
			)
		else:
			avg_response_time = min_response_time = max_response_time = 0
			median_response_time = p95_response_time = p99_response_time = 0

		requests_per_second = (
			total_requests / total_duration if total_duration > 0 else 0
		)
		error_rate = (
			(failed_requests / total_requests * 100) if total_requests > 0 else 0
		)

		return PerformanceMetrics(
			endpoint=f'MCP:{tool_name}',
			total_requests=total_requests,
			successful_requests=successful_requests,
			failed_requests=failed_requests,
			avg_response_time=avg_response_time * 1000,
			min_response_time=min_response_time * 1000,
			max_response_time=max_response_time * 1000,
			median_response_time=median_response_time * 1000,
			p95_response_time=p95_response_time * 1000,
			p99_response_time=p99_response_time * 1000,
			requests_per_second=requests_per_second,
			error_rate=error_rate,
			total_duration=total_duration,
		)

	def collect_system_metrics(self) -> SystemMetrics:
		"""收集系统指标"""
		# CPU 使用率
		cpu_percent = psutil.cpu_percent(interval=1)

		# 内存使用情况
		memory = psutil.virtual_memory()
		memory_percent = memory.percent
		memory_used_mb = memory.used / (1024 * 1024)
		memory_available_mb = memory.available / (1024 * 1024)

		# 磁盘 I/O
		disk_io = psutil.disk_io_counters()
		disk_io_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
		disk_io_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0

		# 网络 I/O
		network_io = psutil.net_io_counters()
		network_io_sent_mb = network_io.bytes_sent / (1024 * 1024) if network_io else 0
		network_io_recv_mb = network_io.bytes_recv / (1024 * 1024) if network_io else 0

		return SystemMetrics(
			cpu_percent=cpu_percent,
			memory_percent=memory_percent,
			memory_used_mb=memory_used_mb,
			memory_available_mb=memory_available_mb,
			disk_io_read_mb=disk_io_read_mb,
			disk_io_write_mb=disk_io_write_mb,
			network_io_sent_mb=network_io_sent_mb,
			network_io_recv_mb=network_io_recv_mb,
		)


class LoadTestScenario:
	"""负载测试场景"""

	def __init__(self, name: str, description: str):
		self.name = name
		self.description = description
		self.metrics: list[PerformanceMetrics] = []

	def add_metrics(self, metrics: PerformanceMetrics):
		"""添加测试指标"""
		self.metrics.append(metrics)

	def get_summary(self) -> dict[str, Any]:
		"""获取测试总结"""
		if not self.metrics:
			return {}

		total_requests = sum(m.total_requests for m in self.metrics)
		total_successful = sum(m.successful_requests for m in self.metrics)
		total_failed = sum(m.failed_requests for m in self.metrics)

		avg_rps = mean(m.requests_per_second for m in self.metrics)
		avg_response_time = mean(m.avg_response_time for m in self.metrics)
		avg_error_rate = mean(m.error_rate for m in self.metrics)

		return {
			'scenario_name': self.name,
			'description': self.description,
			'total_requests': total_requests,
			'successful_requests': total_successful,
			'failed_requests': total_failed,
			'overall_error_rate': avg_error_rate,
			'avg_requests_per_second': avg_rps,
			'avg_response_time_ms': avg_response_time,
			'test_count': len(self.metrics),
		}


class PerformanceReporter:
	"""性能测试报告生成器"""

	def __init__(self):
		self.scenarios: list[LoadTestScenario] = []
		self.system_metrics: list[SystemMetrics] = []

	def add_scenario(self, scenario: LoadTestScenario):
		"""添加测试场景"""
		self.scenarios.append(scenario)

	def add_system_metrics(self, metrics: SystemMetrics):
		"""添加系统指标"""
		self.system_metrics.append(metrics)

	def generate_report(self, output_file: str = 'performance_report.json') -> str:
		"""生成性能测试报告"""
		report = {
			'test_metadata': {
				'generated_at': datetime.now().isoformat(),
				'total_scenarios': len(self.scenarios),
				'test_duration_minutes': len(self.system_metrics)
				if self.system_metrics
				else 0,
			},
			'scenarios': [scenario.get_summary() for scenario in self.scenarios],
			'detailed_metrics': [],
			'system_metrics': [],
		}

		# 添加详细指标
		for scenario in self.scenarios:
			for metrics in scenario.metrics:
				report['detailed_metrics'].append(
					{
						'scenario': scenario.name,
						'endpoint': metrics.endpoint,
						'total_requests': metrics.total_requests,
						'successful_requests': metrics.successful_requests,
						'failed_requests': metrics.failed_requests,
						'avg_response_time_ms': metrics.avg_response_time,
						'min_response_time_ms': metrics.min_response_time,
						'max_response_time_ms': metrics.max_response_time,
						'median_response_time_ms': metrics.median_response_time,
						'p95_response_time_ms': metrics.p95_response_time,
						'p99_response_time_ms': metrics.p99_response_time,
						'requests_per_second': metrics.requests_per_second,
						'error_rate': metrics.error_rate,
						'total_duration': metrics.total_duration,
					}
				)

		# 添加系统指标
		for i, metrics in enumerate(self.system_metrics):
			report['system_metrics'].append(
				{
					'timestamp': i,  # 简化的时间戳
					'cpu_percent': metrics.cpu_percent,
					'memory_percent': metrics.memory_percent,
					'memory_used_mb': metrics.memory_used_mb,
					'memory_available_mb': metrics.memory_available_mb,
					'disk_io_read_mb': metrics.disk_io_read_mb,
					'disk_io_write_mb': metrics.disk_io_write_mb,
					'network_io_sent_mb': metrics.network_io_sent_mb,
					'network_io_recv_mb': metrics.network_io_recv_mb,
				}
			)

		# 保存报告
		with open(output_file, 'w', encoding='utf-8') as f:
			json.dump(report, f, indent=2, ensure_ascii=False)

		print(f'\n📊 性能测试报告已保存到: {output_file}')
		return output_file

	def print_summary(self):
		"""打印测试总结"""
		print('\n' + '=' * 80)
		print('📊 性能测试总结报告')
		print('=' * 80)

		for scenario in self.scenarios:
			summary = scenario.get_summary()
			print(f'\n🎯 场景: {summary["scenario_name"]}')
			print(f'   描述: {summary["description"]}')
			print(f'   总请求数: {summary["total_requests"]}')
			print(f'   成功请求: {summary["successful_requests"]}')
			print(f'   失败请求: {summary["failed_requests"]}')
			print(f'   错误率: {summary["overall_error_rate"]:.2f}%')
			print(f'   平均 RPS: {summary["avg_requests_per_second"]:.2f}')
			print(f'   平均响应时间: {summary["avg_response_time_ms"]:.2f}ms')

		if self.system_metrics:
			print('\n💻 系统资源使用情况:')
			avg_cpu = mean(m.cpu_percent for m in self.system_metrics)
			avg_memory = mean(m.memory_percent for m in self.system_metrics)
			max_memory = max(m.memory_used_mb for m in self.system_metrics)

			print(f'   平均 CPU 使用率: {avg_cpu:.1f}%')
			print(f'   平均内存使用率: {avg_memory:.1f}%')
			print(f'   峰值内存使用: {max_memory:.1f}MB')


async def run_performance_tests():
	"""运行性能测试"""
	print('🚀 OpenAPI MCP 性能测试套件')
	print('=' * 60)

	# 创建测试应用
	app = create_performance_test_app()

	# 集成 MCP 服务器
	mcp_server = OpenApiMcpServer(app)
	mcp_server.mount('/mcp')

	# 在后台启动服务器
	import threading

	import uvicorn

	def run_server():
		uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')

	server_thread = threading.Thread(target=run_server, daemon=True)
	server_thread.start()

	# 等待服务器启动
	await asyncio.sleep(3)

	# 创建性能测试器和报告生成器
	async with PerformanceTester() as tester:
		reporter = PerformanceReporter()

		# 测试场景1: 基础端点性能测试
		print('\n📋 场景1: 基础端点性能测试')
		scenario1 = LoadTestScenario('基础端点测试', '测试不同复杂度的基础端点性能')

		endpoints = [
			('/simple', '简单端点'),
			('/medium', '中等复杂度端点'),
			('/complex', '复杂端点'),
			('/large-data', '大数据端点'),
		]

		for endpoint, description in endpoints:
			metrics = await tester.test_endpoint_performance(
				endpoint, concurrent_users=10, requests_per_user=50
			)
			scenario1.add_metrics(metrics)

			print(
				f'  ✅ {description}: RPS={metrics.requests_per_second:.1f}, '
				f'响应时间={metrics.avg_response_time:.1f}ms, '
				f'错误率={metrics.error_rate:.1f}%'
			)

		reporter.add_scenario(scenario1)

		# 测试场景2: 并发压力测试
		print('\n📋 场景2: 并发压力测试')
		scenario2 = LoadTestScenario('并发压力测试', '测试高并发情况下的性能表现')

		for concurrent_users in [20, 50, 100]:
			metrics = await tester.test_endpoint_performance(
				'/medium', concurrent_users=concurrent_users, requests_per_user=20
			)
			scenario2.add_metrics(metrics)

			print(
				f'  ✅ {concurrent_users} 并发用户: RPS={metrics.requests_per_second:.1f}, '
				f'响应时间={metrics.avg_response_time:.1f}ms, '
				f'错误率={metrics.error_rate:.1f}%'
			)

		reporter.add_scenario(scenario2)

		# 测试场景3: MCP 工具性能测试
		print('\n📋 场景3: MCP 工具性能测试')
		scenario3 = LoadTestScenario('MCP工具测试', '测试 MCP 工具的性能')

		mcp_tools = ['search_endpoints', 'generate_examples']

		for tool in mcp_tools:
			try:
				metrics = await tester.test_mcp_performance(
					tool, concurrent_users=5, requests_per_user=10
				)
				scenario3.add_metrics(metrics)

				print(
					f'  ✅ {tool}: RPS={metrics.requests_per_second:.1f}, '
					f'响应时间={metrics.avg_response_time:.1f}ms, '
					f'错误率={metrics.error_rate:.1f}%'
				)
			except Exception as e:
				print(f'  ❌ {tool}: 测试失败 - {e}')

		reporter.add_scenario(scenario3)

		# 测试场景4: 持久负载测试
		print('\n📋 场景4: 持久负载测试')
		scenario4 = LoadTestScenario('持久负载测试', '测试系统在持续负载下的稳定性')

		# 收集系统指标
		for i in range(5):  # 5次测试，每次间隔10秒
			if i > 0:
				await asyncio.sleep(10)

			system_metrics = tester.collect_system_metrics()
			reporter.add_system_metrics(system_metrics)

			metrics = await tester.test_endpoint_performance(
				'/medium', concurrent_users=20, requests_per_user=30
			)
			scenario4.add_metrics(metrics)

			print(
				f'  ✅ 第{i + 1}轮: RPS={metrics.requests_per_second:.1f}, '
				f'CPU={system_metrics.cpu_percent:.1f}%, '
				f'内存={system_metrics.memory_percent:.1f}%'
			)

		reporter.add_scenario(scenario4)

		# 生成报告
		report_file = reporter.generate_report()
		reporter.print_summary()

		# 性能基准测试
		print('\n🎯 性能基准对比')
		print('-' * 40)

		for scenario in reporter.scenarios:
			if scenario.metrics:
				best_rps = max(m.requests_per_second for m in scenario.metrics)
				best_response = min(m.avg_response_time for m in scenario.metrics)
				worst_response = max(m.avg_response_time for m in scenario.metrics)

				print(f'{scenario.name}:')
				print(f'   最高 RPS: {best_rps:.1f}')
				print(f'   最快响应: {best_response:.1f}ms')
				print(f'   最慢响应: {worst_response:.1f}ms')

		return report_file


def main():
	"""主函数"""
	print('🔧 OpenAPI MCP 性能测试示例')
	print('=' * 60)

	# 安装依赖检查
	required_packages = ['aiohttp', 'psutil']
	missing_packages = []

	for package in required_packages:
		try:
			__import__(package)
		except ImportError:
			missing_packages.append(package)

	if missing_packages:
		print(f'❌ 缺少必需的包: {", ".join(missing_packages)}')
		print('请运行: pip install aiohttp psutil')
		return

	# 运行性能测试
	try:
		report_file = asyncio.run(run_performance_tests())
		print(f'\n✅ 性能测试完成！报告文件: {report_file}')
	except Exception as e:
		print(f'❌ 性能测试失败: {e}')
		import traceback

		traceback.print_exc()


if __name__ == '__main__':
	main()
