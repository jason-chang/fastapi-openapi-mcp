"""
纯文本格式化器

将 OpenAPI 数据转换为纯文本格式的输出。
"""

from typing import Any

from openapi_mcp.formatters.base import BaseFormatter


class PlainTextFormatter(BaseFormatter):
	"""纯文本格式化器

	将 OpenAPI 数据格式化为简洁的纯文本输出，
	不包含任何特殊格式标记，适合在不支持富文本的环境中使用。
	"""

	def format_endpoints(
		self, grouped_endpoints: dict[str, list[dict[str, str]]]
	) -> str:
		"""格式化接口列表为纯文本

		Args:
			grouped_endpoints: 按标签分组的接口列表

		Returns:
			纯文本格式的接口列表
		"""
		if not grouped_endpoints:
			return 'No endpoints found.'

		lines = ['Available API Endpoints:', '']

		# 统计总接口数
		total_endpoints = sum(
			len(endpoints) for endpoints in grouped_endpoints.values()
		)

		# 按标签分组输出
		for tag, endpoints in grouped_endpoints.items():
			# 标签名称
			tag_display = tag if tag != 'Untagged' else 'Untagged'
			lines.append(f'[{tag_display}]')

			# 接口列表
			for endpoint in endpoints:
				method = endpoint['method'].upper()
				path = endpoint['path']
				summary = endpoint.get('summary', 'No description')

				lines.append(f'  {method} {path} - {summary}')

			lines.append('')  # 空行分隔

		# 总结
		lines.append(f'Total endpoints: {total_endpoints}')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_endpoint_details(self, endpoint_info: dict[str, Any]) -> str:
		"""格式化接口详情为纯文本

		Args:
			endpoint_info: 接口详细信息

		Returns:
			纯文本格式的接口详情
		"""
		lines = []

		# 基本信息
		method = endpoint_info.get('method', 'UNKNOWN').upper()
		path = endpoint_info.get('path', '')
		summary = endpoint_info.get('summary', '')
		description = endpoint_info.get('description', '')

		lines.append(f'{method} {path}')
		lines.append('=' * (len(method) + len(path) + 1))
		lines.append('')

		if summary:
			lines.append(summary)
			lines.append('')

		if description:
			lines.append(description)
			lines.append('')

		# 废弃状态
		if endpoint_info.get('deprecated'):
			lines.append('WARNING: This endpoint is deprecated.')
			lines.append('')

		# 参数
		parameters = endpoint_info.get('parameters', [])
		if parameters:
			lines.append('Parameters:')
			for param in parameters:
				name = param.get('name', 'unknown')
				in_location = param.get('in', 'unknown')
				required = ' [Required]' if param.get('required') else ''
				param_type = param.get('type', 'unknown')
				param_description = param.get('description', '')

				lines.append(f'  - {name} ({in_location}){required}: {param_type}')
				if param_description:
					lines.append(f'    {param_description}')

			lines.append('')

		# 请求体
		request_body = endpoint_info.get('requestBody')
		if request_body:
			lines.append('Request Body:')

			required = ' [Required]' if request_body.get('required') else ''
			lines.append(f'  Required:{required}')

			content = request_body.get('content', {})
			for media_type, schema_info in content.items():
				lines.append(f'  Content-Type: {media_type}')

				if 'schema' in schema_info:
					schema = schema_info['schema']
					if '$ref' in schema:
						ref = schema['$ref'].split('/')[-1]
						lines.append(f'  Schema: {ref}')

			lines.append('')

		# 响应
		responses = endpoint_info.get('responses', {})
		if responses:
			lines.append('Responses:')

			for status_code, response_info in responses.items():
				description = response_info.get('description', 'No description')
				lines.append(f'  {status_code} - {description}')

				content = response_info.get('content', {})
				for media_type, schema_info in content.items():
					lines.append(f'    Content-Type: {media_type}')

					if 'schema' in schema_info:
						schema = schema_info['schema']
						if '$ref' in schema:
							ref = schema['$ref'].split('/')[-1]
							lines.append(f'    Schema: {ref}')

			lines.append('')

		# 认证要求
		security = endpoint_info.get('security', [])
		if security:
			lines.append('Security:')
			for sec_req in security:
				for sec_name, scopes in sec_req.items():
					lines.append(f'  - {sec_name}')
					if scopes:
						lines.append(f'    Scopes: {", ".join(scopes)}')
			lines.append('')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_models(self, models: list[dict[str, str]]) -> str:
		"""格式化数据模型列表为纯文本

		Args:
			models: 模型列表

		Returns:
			纯文本格式的模型列表
		"""
		if not models:
			return 'No models found.'

		lines = [f'API Data Models ({len(models)} models):', '']

		for model in models:
			name = model['name']
			description = model.get('description', 'No description')
			lines.append(f'  - {name}: {description}')

		lines.append('')
		lines.append('Use get_model_details to view full schema.')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_model_details(self, model_info: dict[str, Any]) -> str:
		"""格式化数据模型详情为纯文本

		Args:
			model_info: 模型详细信息

		Returns:
			纯文本格式的模型详情
		"""
		lines = []

		# 基本信息
		name = model_info.get('name', 'Unknown')
		description = model_info.get('description', '')

		lines.append(f'Model: {name}')
		lines.append('=' * (len(name) + 7))
		lines.append('')

		if description:
			lines.append(f'Description: {description}')
			lines.append('')

		# 字段列表
		fields = model_info.get('fields', [])
		if fields:
			lines.append('Fields:')

			for field in fields:
				field_name = field.get('name', 'unknown')
				field_type = field.get('type', 'unknown')
				field_description = field.get('description', '')
				required = ' [Required]' if field.get('required') else ''

				lines.append(f'  - {field_name}{required}: {field_type}')

				if field_description:
					lines.append(f'    {field_description}')

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
					lines.append(f'    ({", ".join(validations)})')

			lines.append('')

		# 必填字段
		required_fields = model_info.get('required', [])
		if required_fields:
			lines.append(f'Required fields: {", ".join(required_fields)}')

		result = '\n'.join(lines)
		return self.truncate(result)

	def format_search_results(self, results: list[dict[str, str]]) -> str:
		"""格式化搜索结果为纯文本

		Args:
			results: 搜索结果列表

		Returns:
			纯文本格式的搜索结果
		"""
		if not results:
			return 'No results found.'

		lines = [f'Search Results ({len(results)} endpoints):', '']

		for result in results:
			method = result.get('method', 'UNKNOWN').upper()
			path = result.get('path', '')
			summary = result.get('summary', 'No description')

			lines.append(f'  {method} {path} - {summary}')

		result_text = '\n'.join(lines)
		return self.truncate(result_text)
