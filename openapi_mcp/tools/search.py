"""
搜索相关的 MCP Tools

提供用于搜索 OpenAPI 接口的增强工具，整合多种搜索功能。
"""

import re
from typing import Any

from mcp.types import CallToolResult, TextContent

from openapi_mcp.tools.base import BaseMcpTool


class SearchEndpointsTool(BaseMcpTool):
	"""搜索 API 接口

	根据关键词在指定范围内搜索接口，支持模糊匹配、正则表达式、
	按标签过滤、按方法过滤等多种搜索方式。

	Attributes:
		name: Tool 名称 'search_endpoints'
		description: Tool 功能描述
		input_schema: 输入参数定义
	"""

	name = 'search_endpoints'
	description = '高级搜索 API 接口，支持关键词、正则表达式、标签、方法等多种搜索方式'
	input_schema = {
		'type': 'object',
		'properties': {
			'keyword': {
				'type': 'string',
				'description': '搜索关键词（支持模糊匹配，不区分大小写）',
			},
			'search_in': {
				'type': 'string',
				'description': '搜索范围',
				'enum': ['path', 'summary', 'description', 'tags', 'all'],
				'default': 'all',
			},
			'regex': {
				'type': 'string',
				'description': '正则表达式搜索（与 keyword 互斥）',
			},
			'tags': {
				'type': 'array',
				'items': {'type': 'string'},
				'description': '按标签过滤，支持多个标签（OR 关系）',
			},
			'methods': {
				'type': 'array',
				'items': {
					'type': 'string',
					'enum': [
						'GET',
						'POST',
						'PUT',
						'DELETE',
						'PATCH',
						'HEAD',
						'OPTIONS',
					],
				},
				'description': '按 HTTP 方法过滤，支持多个方法',
			},
			'include_deprecated': {
				'type': 'boolean',
				'description': '是否包含已废弃的接口',
				'default': False,
			},
			'limit': {
				'type': 'integer',
				'minimum': 1,
				'maximum': 100,
				'description': '返回结果数量限制',
				'default': 50,
			},
		},
		'required': [],
	}

	async def execute(self, **kwargs: Any) -> CallToolResult:
		"""执行搜索工具逻辑

		从 OpenAPI schema 中搜索匹配条件的接口，
		支持多种搜索方式，并格式化为 Markdown 输出。

		Args:
			**kwargs: 搜索参数

		Returns:
			包含搜索结果的 CallToolResult
		"""
		try:
			# 验证参数
			validation_result = self._validate_params(kwargs)
			if validation_result:
				return validation_result

			# 获取搜索参数
			keyword = kwargs.get('keyword', '').strip()
			regex = kwargs.get('regex', '').strip()

			# 获取 OpenAPI spec
			spec = self.get_openapi_spec()

			# 执行搜索
			results = self._search_endpoints_advanced(spec, **kwargs)

			# 限制结果数量
			limit = kwargs.get('limit', 50)
			if len(results) > limit:
				results = results[:limit]
				truncated = True
			else:
				truncated = False

			# 格式化输出 - 即使没有结果也要传递搜索信息
			keyword_or_regex = keyword or regex
			search_in_param = kwargs.get('search_in', 'all')
			if not results and keyword_or_regex:
				# 创建一个假结果对象用于格式化，只包含搜索信息
				fake_results = [
					{
						'keyword': keyword_or_regex,
						'search_in': search_in_param,
						'method': '',
						'path': '',
						'summary': '',
						'description': '',
						'tags': '',
						'matched_in': '',
						'deprecated': False,
					}
				]

				# 检查formatter类型并调用相应方法
				if hasattr(self._formatter, '__class__') and 'Markdown' in self._formatter.__class__.__name__:
					output = self._formatter.format_search_results(
						results=fake_results,
						truncated=truncated,
						empty_results=True,
					)
				else:
					output = self._formatter.format_search_results(fake_results)
			else:
				# 检查formatter类型并调用相应方法
				if hasattr(self._formatter, '__class__') and 'Markdown' in self._formatter.__class__.__name__:
					output = self._formatter.format_search_results(results=results, truncated=truncated)
				else:
					output = self._formatter.format_search_results(results)

			return CallToolResult(content=[TextContent(type='text', text=output)])

		except Exception as e:
			error_msg = f'❌ 错误: 搜索失败 - {type(e).__name__}: {e}'
			return CallToolResult(
				content=[TextContent(type='text', text=error_msg)], isError=True
			)

	def _validate_params(self, params: dict[str, Any]) -> CallToolResult | None:
		"""验证输入参数

		Args:
			params: 输入参数字典

		Returns:
			如果有错误返回 CallToolResult，否则返回 None
		"""
		keyword = params.get('keyword', '').strip()
		regex = params.get('regex', '').strip()

		# keyword 和 regex 不能同时为空
		if not keyword and not regex:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text='❌ 错误: 搜索关键词不能为空',
					)
				],
				isError=True,
			)

		# keyword 和 regex 不能同时提供
		if keyword and regex:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text='❌ 错误: keyword 和 regex 参数不能同时提供',
					)
				],
				isError=True,
			)

		# 验证正则表达式
		if regex:
			try:
				re.compile(regex)
			except re.error as e:
				return CallToolResult(
					content=[
						TextContent(
							type='text',
							text=f'❌ 错误: 无效的正则表达式 - {e}',
						)
					],
					isError=True,
				)

		# 验证搜索范围
		search_in = params.get('search_in', 'all').lower()
		if search_in not in ['path', 'summary', 'description', 'tags', 'all']:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text=f'❌ 错误: 无效的搜索范围 "{search_in}"，'
						'必须是 path, summary, description, tags 或 all',
					)
				],
				isError=True,
			)

		return None

	def _search_endpoints_advanced(
		self, spec: dict[str, Any], **kwargs
	) -> list[dict[str, Any]]:
		"""高级搜索接口

		Args:
			spec: OpenAPI specification 字典
			**kwargs: 搜索参数

		Returns:
			匹配的接口列表
		"""
		results: list[dict[str, Any]] = []
		paths = spec.get('paths', {})

		# 获取搜索参数
		keyword = kwargs.get('keyword', '').strip()
		regex = kwargs.get('regex', '').strip()
		search_in = kwargs.get('search_in', 'all').lower()
		tags_filter = kwargs.get('tags', [])
		methods_filter = [m.upper() for m in kwargs.get('methods', [])]
		include_deprecated = kwargs.get('include_deprecated', False)

		# 编译正则表达式
		regex_pattern = re.compile(regex, re.IGNORECASE) if regex else None
		keyword_lower = keyword.lower() if keyword else None

		# 用于格式化的搜索词显示
		search_term_display = keyword or regex

		for path, methods in paths.items():
			if not isinstance(methods, dict):
				continue

			for method, info in methods.items():
				# 只处理标准 HTTP 方法
				method_upper = method.upper()
				if method_upper not in [
					'GET',
					'POST',
					'PUT',
					'DELETE',
					'PATCH',
					'HEAD',
					'OPTIONS',
				]:
					continue

				if not isinstance(info, dict):
					continue

				# 方法过滤
				if methods_filter and method_upper not in methods_filter:
					continue

				# 废弃接口过滤
				if not include_deprecated and info.get('deprecated', False):
					continue

				# 获取接口信息
				summary = info.get('summary', '') or ''
				description = info.get('description', '') or ''
				tags = [t for t in info.get('tags', []) if isinstance(t, str)]

				# 标签过滤
				if tags_filter:
					if not any(tag in tags_filter for tag in tags):
						continue

				# 执行搜索
				matched_in = self._check_match_advanced(
					path,
					summary,
					description,
					tags,
					keyword_lower,
					regex_pattern,
					search_in,
				)

				if matched_in:
					results.append(
						{
							'method': method_upper,
							'path': path,
							'summary': summary,
							'description': description,
							'tags': ', '.join(tags),
							'matched_in': matched_in,
							'deprecated': info.get('deprecated', False),
							'keyword': search_term_display,
							'search_in': search_in,
						}
					)

		# 按路径和方法排序
		results.sort(key=lambda x: (x['path'], x['method']))

		return results

	def _check_match_advanced(
		self,
		path: str,
		summary: str,
		description: str,
		tags: list[str],
		keyword: str | None,
		regex_pattern: re.Pattern | None,
		search_in: str,
	) -> str | None:
		"""检查接口是否匹配搜索条件

		Args:
			path: 接口路径
			summary: 接口摘要
			description: 接口描述
			tags: 接口标签列表
			keyword: 搜索关键词（已转为小写）
			regex_pattern: 编译后的正则表达式
			search_in: 搜索范围

		Returns:
			匹配的位置，不匹配返回 None
		"""
		# 搜索文本
		search_texts = []
		if search_in in ['path', 'all']:
			search_texts.append(('path', path))
		if search_in in ['summary', 'all']:
			search_texts.append(('summary', summary))
		if search_in in ['description', 'all']:
			search_texts.append(('description', description))
		if search_in in ['tags', 'all']:
			search_texts.append(('tags', ' '.join(tags)))

		# 执行匹配
		for field_name, text in search_texts:
			if keyword and keyword in text.lower():
				return field_name
			if regex_pattern and regex_pattern.search(text):
				return field_name

		return None
