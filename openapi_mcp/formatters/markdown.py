"""
Markdown 格式化器

将 OpenAPI 数据转换为 Markdown 格式的输出。
"""

import json
from typing import Any

from openapi_mcp.formatters.base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
	"""Markdown 格式化器

	将 OpenAPI 数据格式化为美观的 Markdown 文本，
	适合在终端或支持 Markdown 的环境中显示。
	"""

	def format_endpoints(
		self, grouped_endpoints: dict[str, list[dict[str, str]]]
	) -> str:
		"""格式化接口列表为 Markdown

		Args:
			grouped_endpoints: 按标签分组的接口列表

		Returns:
			Markdown 格式的接口列表
		"""
		if not grouped_endpoints:
			return '📭 **No endpoints found.**'

		lines = ['🚀 **Available API Endpoints:**\n']

		# 统计总接口数
		total_endpoints = sum(
			len(endpoints) for endpoints in grouped_endpoints.values()
		)

		# 按标签分组输出
		for tag, endpoints in grouped_endpoints.items():
			# 标签名称（无标签用特殊标记）
			tag_display = tag if tag != 'Untagged' else '📂 Untagged'
			lines.append(f'## {tag_display}\n')

			# 接口列表
			for endpoint in endpoints:
				method = endpoint['method'].upper()
				path = endpoint['path']
				summary = endpoint.get('summary', 'No description')

				lines.append(f'- **{method}** `{path}` - {summary}')

			lines.append('')  # 空行分隔

		# 总结
		lines.append(f'📊 **Total endpoints:** {total_endpoints}')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_endpoint_details(self, endpoint_info: dict[str, Any]) -> str:
		"""格式化接口详情为 Markdown

		Args:
			endpoint_info: 接口详细信息

		Returns:
			Markdown 格式的接口详情
		"""
		lines = []

		# 基本信息
		method = endpoint_info.get('method', 'UNKNOWN').upper()
		path = endpoint_info.get('path', '')
		summary = endpoint_info.get('summary', '')
		description = endpoint_info.get('description', '')

		lines.append(f'# {method} {path}\n')

		if summary:
			lines.append(f'**{summary}**\n')

		if description:
			lines.append(f'{description}\n')

		# 废弃状态
		if endpoint_info.get('deprecated'):
			lines.append('⚠️ **Deprecated**: This endpoint is deprecated.\n')

		# 参数
		parameters = endpoint_info.get('parameters', [])
		if parameters:
			lines.append('## 📝 Parameters\n')
			for param in parameters:
				name = param.get('name', 'unknown')
				in_location = param.get('in', 'unknown')
				required = ' *[Required]*' if param.get('required') else ''
				param_type = param.get('type', 'unknown')
				param_description = param.get('description', '')

				lines.append(f'- **{name}** ({in_location}){required}: `{param_type}`')
				if param_description:
					lines.append(f'  {param_description}')

			lines.append('')

		# 请求体
		request_body = endpoint_info.get('requestBody')
		if request_body:
			lines.append('## 📤 Request Body\n')

			required = ' *[Required]*' if request_body.get('required') else ''
			lines.append(f'**Required:** {required}\n')

			content = request_body.get('content', {})
			for media_type, schema_info in content.items():
				lines.append(f'**Content-Type:** `{media_type}`\n')

				if 'schema' in schema_info:
					schema = schema_info['schema']
					if '$ref' in schema:
						ref = schema['$ref'].split('/')[-1]
						lines.append(f'**Schema:** Reference to `{ref}`\n')
					else:
						lines.append('**Schema:**\n')
						lines.append(
							f'```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n'
						)

				# 示例
				if 'example' in schema_info:
					lines.append('**Example:**\n')
					lines.append(
						f'```json\n{json.dumps(schema_info["example"], indent=2, ensure_ascii=False)}\n```\n'
					)

		# 响应
		responses = endpoint_info.get('responses', {})
		if responses:
			lines.append('## 📥 Responses\n')

			for status_code, response_info in responses.items():
				description = response_info.get('description', 'No description')
				lines.append(f'### {status_code} - {description}\n')

				content = response_info.get('content', {})
				for media_type, schema_info in content.items():
					lines.append(f'**Content-Type:** `{media_type}`\n')

					if 'schema' in schema_info:
						schema = schema_info['schema']
						if '$ref' in schema:
							ref = schema['$ref'].split('/')[-1]
							lines.append(f'**Schema:** Reference to `{ref}`\n')
						else:
							lines.append('**Schema:**\n')
							lines.append(
								f'```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n'
							)

					# 示例
					if 'example' in schema_info:
						lines.append('**Example:**\n')
						lines.append(
							f'```json\n{json.dumps(schema_info["example"], indent=2, ensure_ascii=False)}\n```\n'
						)

		# 认证要求
		security = endpoint_info.get('security', [])
		if security:
			lines.append('## 🔐 Security\n')
			for sec_req in security:
				for sec_name, scopes in sec_req.items():
					lines.append(f'- **{sec_name}**')
					if scopes:
						lines.append(f'  - Scopes: {", ".join(scopes)}')
			lines.append('')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_models(self, models: list[dict[str, str]]) -> str:
		"""格式化数据模型列表为 Markdown

		Args:
			models: 模型列表

		Returns:
			Markdown 格式的模型列表
		"""
		if not models:
			return '📭 **No models found.**'

		lines = [f'📦 **API Data Models ({len(models)} models):**\n']

		for model in models:
			name = model['name']
			description = model.get('description', 'No description')
			lines.append(f'- **{name}**: {description}')

		lines.append('\n💡 Use `get_model_details` to view full schema.')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_model_details(self, model_info: dict[str, Any]) -> str:
		"""格式化数据模型详情为 Markdown

		Args:
			model_info: 模型详细信息

		Returns:
			Markdown 格式的模型详情
		"""
		lines = []

		# 基本信息
		name = model_info.get('name', 'Unknown')
		description = model_info.get('description', '')

		lines.append(f'📦 **Model: {name}**\n')

		if description:
			lines.append(f'**Description:** {description}\n')

		# 字段列表
		fields = model_info.get('fields', [])
		if fields:
			lines.append('## 📋 Fields\n')

			for field in fields:
				field_name = field.get('name', 'unknown')
				field_type = field.get('type', 'unknown')
				field_description = field.get('description', '')
				required = ' *[Required]*' if field.get('required') else ''

				lines.append(f'- **{field_name}**{required}: `{field_type}`')

				if field_description:
					lines.append(f'  {field_description}')

				# 验证规则
				validations = []
				if 'minLength' in field:
					validations.append(f'minLength: {field["minLength"]}')
				if 'maxLength' in field:
					validations.append(f'maxLength: {field["maxLength"]}')
				if 'pattern' in field:
					validations.append(f'pattern: {field["pattern"]}')
				if 'minimum' in field:
					validations.append(f'minimum: {field["minimum"]}')
				if 'maximum' in field:
					validations.append(f'maximum: {field["maximum"]}')
				if 'format' in field:
					validations.append(f'format: {field["format"]}')

				if validations:
					lines.append(f'  ({", ".join(validations)})')

		# 必填字段
		required_fields = model_info.get('required', [])
		if required_fields:
			lines.append(
				f'\n**Required fields:** {", ".join(f"`{f}`" for f in required_fields)}'
			)

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_search_results(
		self,
		results: list[dict[str, Any]],
		truncated: bool = False,
		empty_results: bool = False,
	) -> str:
		"""格式化搜索结果为 Markdown

		Args:
			results: 搜索结果列表
			truncated: 是否结果被截断
			empty_results: 是否为空结果（但仍需要显示搜索信息）

		Returns:
			Markdown 格式的搜索结果
		"""
		if not results and not empty_results:
			return '📭 **没有找到匹配的接口**\n\n**建议**:\n- 尝试使用更通用的关键词\n- 检查拼写是否正确\n- 使用正则表达式搜索'

		# 从第一个结果获取搜索信息
		keyword = results[0].get('keyword', '') if results else ''
		search_in = results[0].get('search_in', 'all') if results else 'all'

		search_in_display = {
			'path': '路径',
			'summary': '摘要',
			'description': '描述',
			'tags': '标签',
			'all': '全部',
		}
		search_in_text = search_in_display.get(search_in, '全部')

		lines = [f'🔍 **搜索结果: "{keyword}"**\n']
		lines.append(f'📊 **搜索范围**: {search_in_text}\n')

		if empty_results:
			lines.append('📈 **匹配数量**: 0 个接口\n')
			lines.append(
				'\n📭 没有找到匹配的接口\n\n**建议**:\n- 尝试使用更通用的关键词\n- 检查拼写是否正确\n- 使用正则表达式搜索'
			)
			return '\n'.join(lines)
		else:
			lines.append(f'📈 **匹配数量**: {len(results)} 个接口\n')

		if truncated:
			lines.append('> ⚠️ **结果被截断** - 仅显示部分结果\n')

		for result in results:
			method = result.get('method', 'UNKNOWN').upper()
			path = result.get('path', '')
			summary = result.get('summary', 'No description')
			description = result.get('description', '')
			tags = result.get('tags', '')
			matched_in = result.get('matched_in', '')
			deprecated = result.get('deprecated', False)

			# 构建接口行
			endpoint_line = f'- **{method}** `{path}`'

			# 添加废弃标记
			if deprecated:
				endpoint_line += ' ⚠️'

			# 添加摘要
			if summary:
				endpoint_line += f' - {summary}'

			lines.append(endpoint_line)

			# 添加匹配位置
			if matched_in:
				matched_in_display = {
					'path': '路径',
					'summary': '摘要',
					'description': '描述',
					'tags': '标签',
				}
				matched_in_text = matched_in_display.get(matched_in, matched_in)
				lines.append(f'  - *匹配于*: {matched_in_text}')

			# 添加标签
			if tags:
				lines.append(f'  - *标签*: {tags}')

			# 添加描述（如果有的话且不重复摘要）
			if description and description != summary:
				lines.append(
					f'  - *描述*: {description[:100]}{"..." if len(description) > 100 else ""}'
				)

			lines.append('')  # 空行分隔

		result_text = '\n'.join(lines)
		return self.truncate(result_text)
