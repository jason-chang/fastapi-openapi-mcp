"""
格式化器基类

定义了所有格式化器必须实现的接口。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseFormatter(ABC):
	"""格式化器基类

	所有格式化器都应继承此基类并实现相应的格式化方法。
	格式化器负责将 OpenAPI 数据转换为特定格式的文本输出。

	Attributes:
		max_length: 最大输出长度（字符数），0 表示不限制
	"""

	def __init__(self, max_length: int = 0) -> None:
		"""初始化格式化器

		Args:
			max_length: 最大输出长度（字符数），0 表示不限制
		"""
		self.max_length = max_length

	@abstractmethod
	def format_endpoints(
		self, grouped_endpoints: dict[str, list[dict[str, str]]]
	) -> str:
		"""格式化接口列表

		Args:
			grouped_endpoints: 按标签分组的接口列表，格式为:
				{
					'tag_name': [
						{'method': 'GET', 'path': '/users', 'summary': '列出用户'},
						...
					],
					...
				}

		Returns:
			格式化后的接口列表文本
		"""
		...

	@abstractmethod
	def format_endpoint_details(self, endpoint_info: dict[str, Any]) -> str:
		"""格式化接口详情

		Args:
			endpoint_info: 接口详细信息字典，包含：
				- path: 接口路径
				- method: HTTP 方法
				- summary: 接口摘要
				- description: 接口描述
				- parameters: 参数列表
				- requestBody: 请求体
				- responses: 响应定义
				- security: 认证要求
				等

		Returns:
			格式化后的接口详情文本
		"""
		...

	@abstractmethod
	def format_models(self, models: list[dict[str, str]]) -> str:
		"""格式化数据模型列表

		Args:
			models: 模型列表，每个模型包含:
				{
					'name': '模型名称',
					'description': '模型描述'
				}

		Returns:
			格式化后的模型列表文本
		"""
		...

	@abstractmethod
	def format_model_details(self, model_info: dict[str, Any]) -> str:
		"""格式化数据模型详情

		Args:
			model_info: 模型详细信息字典，包含：
				- name: 模型名称
				- description: 模型描述
				- fields: 字段列表
				- required: 必填字段列表
				等

		Returns:
			格式化后的模型详情文本
		"""
		...

	@abstractmethod
	def format_search_results(self, results: list[dict[str, str]]) -> str:
		"""格式化搜索结果

		Args:
			results: 搜索结果列表，每个结果包含:
				{
					'method': 'GET',
					'path': '/users',
					'summary': '列出用户'
				}

		Returns:
			格式化后的搜索结果文本
		"""
		...

	def truncate(self, text: str) -> str:
		"""截断文本到最大长度

		如果文本超过 max_length，会被截断并添加省略标记。
		如果 max_length 为 0，则不进行截断。

		Args:
			text: 要截断的文本

		Returns:
			截断后的文本
		"""
		if self.max_length <= 0 or len(text) <= self.max_length:
			return text

		# 留出省略标记的空间
		truncated = text[: self.max_length - 100]
		truncated += '\n\n...\n\n'
		truncated += (
			f'⚠️ 输出已截断（总长度: {len(text)} 字符，限制: {self.max_length} 字符）'
		)

		return truncated
