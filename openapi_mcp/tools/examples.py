"""
示例生成相关的 MCP Tools

提供用于生成 API 调用示例的工具。
"""

import json
from typing import Any

from mcp.types import CallToolResult, TextContent

from openapi_mcp.tools.base import BaseMcpTool


class GenerateExampleTool(BaseMcpTool):
	"""生成 API 调用示例

	根据 OpenAPI 规范生成各种格式的调用示例，包括 JSON、cURL、Python、
	JavaScript 等。支持自定义示例策略和处理复杂引用结构。

	Attributes:
		name: Tool 名称 'generate_examples'
		description: Tool 功能描述
		input_schema: 输入参数定义
	"""

	name = 'generate_examples'
	description = '根据 OpenAPI 规范生成各种格式的 API 调用示例'
	input_schema = {
		'type': 'object',
		'properties': {
			'path': {
				'type': 'string',
				'description': '接口路径，例如 /api/v1/users',
			},
			'method': {
				'type': 'string',
				'description': 'HTTP 方法，例如 GET, POST, PUT, DELETE',
				'enum': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
			},
			'formats': {
				'type': 'array',
				'items': {
					'type': 'string',
					'enum': ['json', 'curl', 'python', 'javascript', 'http', 'postman'],
				},
				'description': '生成的示例格式，默认生成所有格式',
			},
			'include_auth': {
				'type': 'boolean',
				'description': '是否包含认证信息',
				'default': True,
			},
			'server_url': {
				'type': 'string',
				'description': '服务器基础 URL，默认使用 OpenAPI 规范中的服务器 URL',
			},
			'example_strategy': {
				'type': 'string',
				'enum': ['minimal', 'complete', 'realistic'],
				'default': 'realistic',
				'description': '示例生成策略',
			},
		},
		'required': ['path', 'method'],
	}

	async def execute(self, **kwargs: Any) -> CallToolResult:
		"""执行示例生成工具逻辑

		Args:
			**kwargs: 生成参数

		Returns:
			包含示例的 CallToolResult
		"""
		try:
			# 验证参数
			validation_result = self._validate_params(kwargs)
			if validation_result:
				return validation_result

			# 获取 OpenAPI spec
			spec = self.get_openapi_spec()

			# 查找接口
			endpoint_info = self._find_endpoint(spec, kwargs['path'], kwargs['method'])
			if not endpoint_info:
				error_msg = f'❌ 错误: 接口不存在 - {kwargs["method"]} {kwargs["path"]}'
				return CallToolResult(
					content=[TextContent(type='text', text=error_msg)], isError=True
				)

			# 准备生成参数
			generate_params = self._prepare_generate_params(spec, kwargs)

			# 生成示例
			examples = self._generate_examples(endpoint_info, generate_params)

			# 格式化输出
			output = self._format_examples_output(examples, kwargs.get('formats', []))

			return CallToolResult(content=[TextContent(type='text', text=output)])

		except Exception as e:
			error_msg = f'❌ 错误: 示例生成失败 - {type(e).__name__}: {e}'
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
		path = params.get('path', '').strip()
		method = params.get('method', '').strip()

		if not path or not method:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text='❌ 错误: path 和 method 参数不能为空',
					)
				],
				isError=True,
			)

		if method.upper() not in [
			'GET',
			'POST',
			'PUT',
			'DELETE',
			'PATCH',
			'HEAD',
			'OPTIONS',
		]:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text=f'❌ 错误: 无效的 HTTP 方法 "{method}"',
					)
				],
				isError=True,
			)

		# 验证格式
		formats = params.get('formats', [])
		valid_formats = ['json', 'curl', 'python', 'javascript', 'http', 'postman']
		if formats and any(f not in valid_formats for f in formats):
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text=f'❌ 错误: 无效的格式，支持的格式: {", ".join(valid_formats)}',
					)
				],
				isError=True,
			)

		# 验证示例策略
		strategy = params.get('example_strategy', 'realistic')
		if strategy not in ['minimal', 'complete', 'realistic']:
			return CallToolResult(
				content=[
					TextContent(
						type='text',
						text=f'❌ 错误: 无效的示例策略 "{strategy}"',
					)
				],
				isError=True,
			)

		return None

	def _find_endpoint(
		self, spec: dict[str, Any], path: str, method: str
	) -> dict[str, Any] | None:
		"""查找接口信息

		Args:
			spec: OpenAPI specification 字典
			path: 接口路径
			method: HTTP 方法

		Returns:
			接口信息字典，如果不存在则返回 None
		"""
		paths = spec.get('paths', {})
		if path not in paths:
			return None

		path_item = paths[path]
		if not isinstance(path_item, dict):
			return None

		endpoint_info = path_item.get(method.lower())
		if not isinstance(endpoint_info, dict):
			return None

		return endpoint_info

	def _prepare_generate_params(
		self, spec: dict[str, Any], kwargs: dict[str, Any]
	) -> dict[str, Any]:
		"""准备生成参数

		Args:
			spec: OpenAPI specification 字典
			kwargs: 输入参数

		Returns:
			生成参数字典
		"""
		# 获取服务器 URL
		server_url = kwargs.get('server_url')
		if not server_url:
			servers = spec.get('servers', [])
			if servers and isinstance(servers, list) and servers:
				server_url = servers[0].get('url', 'https://api.example.com')
			else:
				server_url = 'https://api.example.com'

		# 获取认证信息
		auth_info = None
		if kwargs.get('include_auth', True):
			auth_info = self._extract_auth_info(spec)

		return {
			'server_url': server_url,
			'auth_info': auth_info,
			'example_strategy': kwargs.get('example_strategy', 'realistic'),
			'path': kwargs['path'],
			'method': kwargs['method'].upper(),
		}

	def _extract_auth_info(self, spec: dict[str, Any]) -> dict[str, Any] | None:
		"""提取认证信息

		Args:
			spec: OpenAPI specification 字典

		Returns:
			认证信息字典
		"""
		security_schemes = spec.get('components', {}).get('securitySchemes', {})
		if not security_schemes:
			return None

		# 简单返回第一个认证方案
		for name, scheme in security_schemes.items():
			if isinstance(scheme, dict):
				return {
					'name': name,
					'type': scheme.get('type', 'unknown'),
					'scheme': scheme,
				}

		return None

	def _generate_examples(
		self, endpoint_info: dict[str, Any], params: dict[str, Any]
	) -> dict[str, Any]:
		"""生成示例

		Args:
			endpoint_info: 接口信息
			params: 生成参数

		Returns:
			生成的示例字典
		"""
		examples = {
			'path': params['path'],
			'method': params['method'],
			'server_url': params['server_url'],
		}

		# 提取接口信息
		parameters = endpoint_info.get('parameters', [])
		request_body = endpoint_info.get('requestBody')
		responses = endpoint_info.get('responses', {})

		# 生成参数示例
		examples['parameters'] = self._generate_parameters_example(
			parameters, params['example_strategy']
		)

		# 生成请求体示例
		if request_body:
			examples['request_body'] = self._generate_request_body_example(
				request_body, params['example_strategy']
			)

		# 生成认证示例
		if params['auth_info']:
			examples['auth'] = self._generate_auth_example(params['auth_info'])

		# 生成响应示例
		examples['responses'] = self._generate_responses_example(
			responses, params['example_strategy']
		)

		return examples

	def _generate_parameters_example(
		self, parameters: list[dict[str, Any]], strategy: str
	) -> dict[str, Any]:
		"""生成参数示例

		Args:
			parameters: 参数列表
			strategy: 生成策略

		Returns:
			参数示例
		"""
		examples = {}

		for param in parameters:
			if not isinstance(param, dict):
				continue

			name = param.get('name', '')
			param_in = param.get('in', '')
			required = param.get('required', False)

			if not name:
				continue

			# 跳过非必需的参数（minimal 策略）
			if strategy == 'minimal' and not required:
				continue

			param_schema = param.get('schema', {})
			if not isinstance(param_schema, dict):
				continue

			example_value = self._generate_value_example(param_schema, strategy)

			# 按位置组织参数
			if param_in not in examples:
				examples[param_in] = {}

			examples[param_in][name] = example_value

		return examples

	def _generate_request_body_example(
		self, request_body: dict[str, Any], strategy: str
	) -> dict[str, Any]:
		"""生成请求体示例

		Args:
			request_body: 请求体定义
			strategy: 生成策略

		Returns:
			请求体示例
		"""
		content = request_body.get('content', {})
		if not isinstance(content, dict):
			return {}

		# 优先使用 JSON 格式
		json_content = content.get('application/json')
		if not json_content or not isinstance(json_content, dict):
			# 使用第一个可用的格式
			for _media_type, media_info in content.items():
				if isinstance(media_info, dict):
					json_content = media_info
					break

		if not json_content:
			return {}

		schema = json_content.get('schema', {})
		if not isinstance(schema, dict):
			return {}

		return {
			'content_type': 'application/json',
			'data': self._generate_value_example(schema, strategy),
		}

	def _generate_auth_example(self, auth_info: dict[str, Any]) -> dict[str, Any]:
		"""生成认证示例

		Args:
			auth_info: 认证信息

		Returns:
			认证示例
		"""
		auth_type = auth_info.get('type', 'unknown')
		scheme = auth_info.get('scheme', {})

		if auth_type == 'http':
			http_scheme = scheme.get('scheme', '').lower()
			if http_scheme == 'bearer':
				return {
					'type': 'Bearer',
					'token': 'your_bearer_token_here',
					'header': 'Authorization: Bearer your_bearer_token_here',
				}
			elif http_scheme == 'basic':
				return {
					'type': 'Basic',
					'username': 'your_username',
					'password': 'your_password',
					'header': 'Authorization: Basic base64(username:password)',
				}

		elif auth_type == 'apiKey':
			return {
				'type': 'API Key',
				'key': scheme.get('name', 'X-API-Key'),
				'value': 'your_api_key_here',
				'location': scheme.get('in', 'header'),
			}

		elif auth_type == 'oauth2':
			return {
				'type': 'OAuth2',
				'access_token': 'your_access_token_here',
				'header': 'Authorization: Bearer your_access_token_here',
			}

		return {'type': auth_type, 'description': '请参考 API 文档获取认证信息'}

	def _generate_responses_example(
		self, responses: dict[str, Any], strategy: str
	) -> dict[str, Any]:
		"""生成响应示例

		Args:
			responses: 响应定义
			strategy: 生成策略

		Returns:
			响应示例
		"""
		examples = {}

		# 优先生成成功响应
		success_codes = ['200', '201', '202', '204']
		for code in success_codes:
			if code in responses and isinstance(responses[code], dict):
				response = responses[code]
				examples[code] = self._generate_single_response_example(
					response, strategy
				)
				break

		# 如果没有成功响应，生成第一个响应
		if not examples and responses:
			for code, response in responses.items():
				if isinstance(response, dict):
					examples[code] = self._generate_single_response_example(
						response, strategy
					)
					break

		return examples

	def _generate_single_response_example(
		self, response: dict[str, Any], strategy: str
	) -> dict[str, Any]:
		"""生成单个响应示例

		Args:
			response: 响应定义
			strategy: 生成策略

		Returns:
			响应示例
		"""
		example = {
			'description': response.get('description', ''),
		}

		content = response.get('content', {})
		if isinstance(content, dict):
			json_content = content.get('application/json')
			if json_content and isinstance(json_content, dict):
				schema = json_content.get('schema', {})
				if isinstance(schema, dict):
					example['data'] = self._generate_value_example(schema, strategy)

		return example

	def _generate_value_example(self, schema: dict[str, Any], strategy: str) -> Any:
		"""根据 schema 生成示例值

		Args:
			schema: JSON Schema
			strategy: 生成策略

		Returns:
			生成的示例值
		"""
		# 处理 $ref 引用
		if '$ref' in schema:
			# 简单处理：返回引用名称
			ref_path = schema['$ref']
			ref_name = ref_path.split('/')[-1]
			return f'#ref:{ref_name}'

		schema_type = schema.get('type', 'object')

		if schema_type == 'object':
			return self._generate_object_example(schema, strategy)
		elif schema_type == 'array':
			return self._generate_array_example(schema, strategy)
		elif schema_type == 'string':
			return self._generate_string_example(schema, strategy)
		elif schema_type == 'number' or schema_type == 'integer':
			return self._generate_number_example(schema, strategy)
		elif schema_type == 'boolean':
			return True
		else:
			return None

	def _generate_object_example(
		self, schema: dict[str, Any], strategy: str
	) -> dict[str, Any]:
		"""生成对象示例

		Args:
			schema: 对象 schema
			strategy: 生成策略

		Returns:
			对象示例
		"""
		example = {}
		properties = schema.get('properties', {})
		required = schema.get('required', [])

		if not isinstance(properties, dict):
			return example

		for prop_name, prop_schema in properties.items():
			if not isinstance(prop_schema, dict):
				continue

			# minimal 策略只生成必需字段
			if strategy == 'minimal' and prop_name not in required:
				continue

			prop_value = self._generate_value_example(prop_schema, strategy)
			example[prop_name] = prop_value

		return example

	def _generate_array_example(
		self, schema: dict[str, Any], strategy: str
	) -> list[Any]:
		"""生成数组示例

		Args:
			schema: 数组 schema
			strategy: 生成策略

		Returns:
			数组示例
		"""
		items = schema.get('items', {})
		if not isinstance(items, dict):
			return []

		item_example = self._generate_value_example(items, strategy)

		# minimal 策略返回单个元素
		if strategy == 'minimal':
			return [item_example]

		# realistic 策略返回 2-3 个元素
		if strategy == 'realistic':
			return [item_example, item_example]

		# complete 策略返回更多元素
		return [item_example, item_example, item_example]

	def _generate_string_example(self, schema: dict[str, Any], strategy: str) -> str:
		"""生成字符串示例

		Args:
			schema: 字符串 schema
			strategy: 生成策略

		Returns:
			字符串示例
		"""
		# 检查枚举值
		if 'enum' in schema and isinstance(schema['enum'], list) and schema['enum']:
			return str(schema['enum'][0])

		# 检查格式
		format_type = schema.get('format', '')

		if format_type == 'email':
			return 'user@example.com'
		elif format_type == 'uri':
			return 'https://example.com/resource'
		elif format_type == 'uuid':
			return '550e8400-e29b-41d4-a716-446655440000'
		elif format_type == 'date':
			return '2023-12-01'
		elif format_type == 'date-time':
			return '2023-12-01T12:00:00Z'
		elif format_type == 'password':
			return 'password123'

		# 根据字段名生成合理的示例
		field_name = schema.get('title', '').lower()
		if 'name' in field_name:
			return 'John Doe'
		elif 'email' in field_name:
			return 'user@example.com'
		elif 'id' in field_name:
			return '12345'
		elif 'url' in field_name:
			return 'https://example.com'

		# 检查长度限制
		min_length = schema.get('minLength', 1)
		max_length = schema.get('maxLength', 50)

		if strategy == 'minimal':
			return 'a' * min_length
		else:
			# 生成合理的示例文本
			example_text = 'example'
			if len(example_text) < min_length:
				example_text += 'a' * (min_length - len(example_text))
			elif len(example_text) > max_length:
				example_text = example_text[:max_length]
			return example_text

	def _generate_number_example(
		self, schema: dict[str, Any], strategy: str
	) -> int | float:
		"""生成数字示例

		Args:
			schema: 数字 schema
			strategy: 生成策略

		Returns:
			数字示例
		"""
		# 检查枚举值
		if 'enum' in schema and isinstance(schema['enum'], list) and schema['enum']:
			return schema['enum'][0]

		schema_type = schema.get('type', 'number')
		minimum = schema.get('minimum', 0)
		maximum = schema.get('maximum', 100)

		if strategy == 'minimal':
			return minimum

		if schema_type == 'integer':
			return min(minimum + 1, maximum)
		else:
			return min(minimum + 1.5, maximum)

	def _format_examples_output(
		self, examples: dict[str, Any], formats: list[str]
	) -> str:
		"""格式化示例输出

		Args:
			examples: 生成的示例
			formats: 要输出的格式列表

		Returns:
			格式化后的输出文本
		"""
		if not formats:
			formats = ['json', 'curl', 'python']

		lines = [f'# 📝 {examples["method"]} {examples["path"]} 调用示例\n']

		# 基本信息行
		lines.append(f'**服务器:** {examples["server_url"]}')
		lines.append('')

		# 生成不同格式的示例
		for format_type in formats:
			if format_type == 'json':
				lines.extend(self._format_json_example(examples))
			elif format_type == 'curl':
				lines.extend(self._format_curl_example(examples))
			elif format_type == 'python':
				lines.extend(self._format_python_example(examples))
			elif format_type == 'javascript':
				lines.extend(self._format_javascript_example(examples))
			elif format_type == 'http':
				lines.extend(self._format_http_example(examples))
			elif format_type == 'postman':
				lines.extend(self._format_postman_example(examples))

		return '\n'.join(lines)

	def _format_json_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 JSON 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## JSON 示例\n']

		# 请求体示例
		if 'request_body' in examples:
			lines.append('### 请求体\n')
			lines.append('```json')
			lines.append(
				json.dumps(
					examples['request_body']['data'], indent=2, ensure_ascii=False
				)
			)
			lines.append('```\n')

		# 响应示例
		if 'responses' in examples:
			lines.append('### 响应\n')
			for status_code, response in examples['responses'].items():
				lines.append(f'#### {status_code}\n')
				if 'data' in response:
					lines.append('```json')
					lines.append(
						json.dumps(response['data'], indent=2, ensure_ascii=False)
					)
					lines.append('```\n')

		return lines

	def _format_curl_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 cURL 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## cURL 示例\n']

		url = f'{examples["server_url"]}{examples["path"]}'
		curl_cmd = ['curl', '-X', examples['method']]

		# 添加请求头
		headers = []

		if 'request_body' in examples:
			content_type = examples['request_body'].get(
				'content_type', 'application/json'
			)
			headers.append(f'Content-Type: {content_type}')

		if 'auth' in examples:
			auth = examples['auth']
			if 'header' in auth:
				headers.append(auth['header'])

		for header in headers:
			curl_cmd.extend(['-H', f"'{header}'"])

		# 添加请求体
		if 'request_body' in examples:
			data = examples['request_body']['data']
			json_data = json.dumps(data, ensure_ascii=False)
			curl_cmd.extend(['-d', f"'{json_data}'"])

		# 添加 URL
		curl_cmd.append(f"'{url}'")

		lines.append('```bash')
		lines.append(' \\\n  '.join(curl_cmd))
		lines.append('```\n')

		return lines

	def _format_python_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 Python 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## Python 示例\n']
		lines.append('```python')
		lines.append('import requests')
		lines.append('import json')

		url = f'{examples["server_url"]}{examples["path"]}'
		lines.append(f'\nurl = "{url}"')

		# 请求头
		headers = {}
		if 'request_body' in examples:
			headers['Content-Type'] = examples['request_body'].get(
				'content_type', 'application/json'
			)

		if 'auth' in examples:
			auth = examples['auth']
			if auth['type'] == 'Bearer':
				headers['Authorization'] = f'Bearer {auth["token"]}'
			elif auth['type'] == 'API Key':
				if auth['location'] == 'header':
					headers[auth['key']] = auth['value']

		if headers:
			lines.append(f'headers = {json.dumps(headers, indent=2)}')

		# 请求体
		if 'request_body' in examples:
			data = examples['request_body']['data']
			lines.append(f'data = {json.dumps(data, indent=2)}')
			lines.append(
				'\nresponse = requests.request("{}", url, headers=headers, json=data)'.format(
					examples['method'].lower()
				)
			)
		else:
			lines.append(
				'\nresponse = requests.request("{}", url, headers=headers)'.format(
					examples['method'].lower()
				)
			)

		lines.append('result = response.json()')
		lines.append('print(result)')
		lines.append('```\n')

		return lines

	def _format_javascript_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 JavaScript 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## JavaScript 示例\n']
		lines.append('```javascript')

		url = f'{examples["server_url"]}{examples["path"]}'
		lines.append(f'const url = "{url}";')

		# 请求头
		if 'request_body' in examples or 'auth' in examples:
			lines.append('const headers = {')
			header_lines = []

			if 'request_body' in examples:
				content_type = examples['request_body'].get(
					'content_type', 'application/json'
				)
				header_lines.append(f'  "Content-Type": "{content_type}"')

			if 'auth' in examples:
				auth = examples['auth']
				if auth['type'] == 'Bearer':
					header_lines.append(f'  "Authorization": "Bearer {auth["token"]}"')

			lines.append(',\n'.join(header_lines))
			lines.append('};')

		# 请求体
		if 'request_body' in examples:
			data = examples['request_body']['data']
			lines.append(f'const data = {json.dumps(data, indent=2)};')
			lines.append('\nfetch(url, {')
			lines.append(f'  method: "{examples["method"]}",')
			if 'request_body' in examples or 'auth' in examples:
				lines.append('  headers,')
			lines.append('  body: JSON.stringify(data)')
			lines.append('})')
		else:
			lines.append('\nfetch(url, {')
			lines.append(f'  method: "{examples["method"]}"')
			if 'auth' in examples:
				lines.append(',  headers')
			lines.append('})')

		lines.append('  .then(response => response.json())')
		lines.append('  .then(data => console.log(data))')
		lines.append('```\n')

		return lines

	def _format_http_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 HTTP 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## HTTP 示例\n']
		lines.append('```http')

		# 请求行
		url = f'{examples["server_url"]}{examples["path"]}'
		lines.append(f'{examples["method"]} {url} HTTP/1.1')

		# 请求头
		if 'request_body' in examples:
			content_type = examples['request_body'].get(
				'content_type', 'application/json'
			)
			lines.append(f'Content-Type: {content_type}')

		if 'auth' in examples:
			auth = examples['auth']
			if 'header' in auth:
				lines.append(auth['header'])

		lines.append('')

		# 请求体
		if 'request_body' in examples:
			data = examples['request_body']['data']
			lines.append(json.dumps(data, ensure_ascii=False))

		lines.append('```\n')

		return lines

	def _format_postman_example(self, examples: dict[str, Any]) -> list[str]:
		"""格式化 Postman 示例

		Args:
			examples: 生成的示例

		Returns:
			格式化后的文本行列表
		"""
		lines = ['## Postman 集合示例\n']
		lines.append('```json')

		postman_collection = {
			'info': {
				'name': f'{examples["method"]} {examples["path"]}',
				'description': 'Auto-generated API request',
			},
			'item': [
				{
					'name': examples['path'],
					'request': {
						'method': examples['method'],
						'header': [],
						'url': {
							'raw': f'{examples["server_url"]}{examples["path"]}',
							'host': [
								examples['server_url']
								.replace('https://', '')
								.replace('http://', '')
							],
							'path': examples['path'].strip('/').split('/'),
						},
					},
				}
			],
		}

		# 添加请求头
		headers = []
		if 'request_body' in examples:
			headers.append(
				{
					'key': 'Content-Type',
					'value': examples['request_body'].get(
						'content_type', 'application/json'
					),
				}
			)

		if 'auth' in examples:
			auth = examples['auth']
			if auth['type'] == 'Bearer':
				headers.append(
					{'key': 'Authorization', 'value': f'Bearer {auth["token"]}'}
				)

		postman_collection['item'][0]['request']['header'] = headers

		# 添加请求体
		if 'request_body' in examples:
			postman_collection['item'][0]['request']['body'] = {
				'mode': 'raw',
				'raw': json.dumps(
					examples['request_body']['data'], indent=2, ensure_ascii=False
				),
				'options': {'raw': {'language': 'json'}},
			}

		lines.append(json.dumps(postman_collection, indent=2, ensure_ascii=False))
		lines.append('```\n')

		return lines
