"""
JSON 格式化器

将 OpenAPI 数据转换为 JSON 格式的输出。
"""

import json
from typing import Any

from openapi_mcp.formatters.base import BaseFormatter


class JsonFormatter(BaseFormatter):
	"""JSON 格式化器

	将 OpenAPI 数据格式化为结构化的 JSON 输出，
	适合程序化处理和与其他系统集成。
	"""

	def format_endpoints(
		self, grouped_endpoints: dict[str, list[dict[str, str]]]
	) -> str:
		"""格式化接口列表为 JSON

		Args:
			grouped_endpoints: 按标签分组的接口列表

		Returns:
			JSON 格式的接口列表
		"""
		result = json.dumps(
			{
				'endpoints': grouped_endpoints,
				'total': sum(len(eps) for eps in grouped_endpoints.values()),
			},
			indent=2,
			ensure_ascii=False,
		)
		return self.truncate(result)

	def format_endpoint_details(self, endpoint_info: dict[str, Any]) -> str:
		"""格式化接口详情为 JSON

		Args:
			endpoint_info: 接口详细信息

		Returns:
			JSON 格式的接口详情
		"""
		result = json.dumps(endpoint_info, indent=2, ensure_ascii=False)
		return self.truncate(result)

	def format_models(self, models: list[dict[str, str]]) -> str:
		"""格式化数据模型列表为 JSON

		Args:
			models: 模型列表

		Returns:
			JSON 格式的模型列表
		"""
		result = json.dumps(
			{'models': models, 'total': len(models)}, indent=2, ensure_ascii=False
		)
		return self.truncate(result)

	def format_model_details(self, model_info: dict[str, Any]) -> str:
		"""格式化数据模型详情为 JSON

		Args:
			model_info: 模型详细信息

		Returns:
			JSON 格式的模型详情
		"""
		result = json.dumps(model_info, indent=2, ensure_ascii=False)
		return self.truncate(result)

	def format_search_results(self, results: list[dict[str, str]]) -> str:
		"""格式化搜索结果为 JSON

		Args:
			results: 搜索结果列表

		Returns:
			JSON 格式的搜索结果
		"""
		result = json.dumps(
			{'results': results, 'total': len(results)}, indent=2, ensure_ascii=False
		)
		return self.truncate(result)
