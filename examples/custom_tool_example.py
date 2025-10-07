"""
自定义 Tool 实例示例

展示如何创建和集成自定义 MCP Tools 到 OpenAPI MCP Server 中。
演示各种类型的自定义工具，包括数据分析、业务逻辑、外部服务等。
"""

import json
import re
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from openapi_mcp.types import ToolDefinition, ToolResult

from openapi_mcp import OpenApiMcpServer
from openapi_mcp.tools.base import BaseTool


# 创建示例 FastAPI 应用
def create_demo_app() -> FastAPI:
	"""创建演示用的 FastAPI 应用"""
	app = FastAPI(
		title='Custom Tools Demo API',
		version='1.0.0',
		description='展示自定义 Tools 的 API',
	)

	@app.get('/products', tags=['products'])
	async def list_products():
		return {'products': []}

	@app.get('/orders', tags=['orders'])
	async def list_orders():
		return {'orders': []}

	@app.get('/users', tags=['users'])
	async def list_users():
		return {'users': []}

	return app


# 自定义工具1: API 分析工具
class ApiAnalyzerTool(BaseTool):
	"""API 分析工具 - 分析 OpenAPI 规范并提供统计信息"""

	def __init__(self):
		super().__init__()
		self.name = 'api_analyzer'
		self.description = '分析 OpenAPI 规范，提供详细的统计和分析信息'

	def get_definition(self) -> ToolDefinition:
		"""获取工具定义"""
		return ToolDefinition(
			name=self.name,
			description=self.description,
			input_schema={
				'type': 'object',
				'properties': {
					'analysis_type': {
						'type': 'string',
						'enum': ['overview', 'endpoints', 'models', 'tags', 'security'],
						'description': '分析类型',
						'default': 'overview',
					},
					'include_details': {
						'type': 'boolean',
						'description': '是否包含详细信息',
						'default': False,
					},
					'filter_tag': {
						'type': 'string',
						'description': '按标签过滤（可选）',
					},
				},
			},
		)

	async def execute(self, arguments: dict[str, Any]) -> ToolResult:
		"""执行工具"""
		try:
			analysis_type = arguments.get('analysis_type', 'overview')
			include_details = arguments.get('include_details', False)
			filter_tag = arguments.get('filter_tag')

			# 获取 OpenAPI 规范
			spec = await self.get_openapi_spec()

			if filter_tag:
				spec = self._filter_spec_by_tag(spec, filter_tag)

			result = self._analyze_spec(spec, analysis_type, include_details)

			return ToolResult(
				success=True, data=result, message=f'API {analysis_type} 分析完成'
			)

		except Exception as e:
			return ToolResult(success=False, error=str(e), message='API 分析失败')

	def _filter_spec_by_tag(self, spec: dict, tag: str) -> dict:
		"""按标签过滤 OpenAPI 规范"""
		filtered_spec = spec.copy()
		filtered_paths = {}

		for path, methods in spec.get('paths', {}).items():
			filtered_methods = {}
			for method, details in methods.items():
				if 'tags' in details and tag in details['tags']:
					filtered_methods[method] = details

			if filtered_methods:
				filtered_paths[path] = filtered_methods

		filtered_spec['paths'] = filtered_paths
		return filtered_spec

	def _analyze_spec(
		self, spec: dict, analysis_type: str, include_details: bool
	) -> dict:
		"""分析 OpenAPI 规范"""
		if analysis_type == 'overview':
			return self._analyze_overview(spec)
		elif analysis_type == 'endpoints':
			return self._analyze_endpoints(spec, include_details)
		elif analysis_type == 'models':
			return self._analyze_models(spec, include_details)
		elif analysis_type == 'tags':
			return self._analyze_tags(spec, include_details)
		elif analysis_type == 'security':
			return self._analyze_security(spec, include_details)
		else:
			raise ValueError(f'未知的分析类型: {analysis_type}')

	def _analyze_overview(self, spec: dict) -> dict:
		"""分析概览信息"""
		info = spec.get('info', {})
		paths = spec.get('paths', {})

		endpoint_count = sum(len(methods) for methods in paths.values())
		path_count = len(paths)

		return {
			'api_info': {
				'title': info.get('title'),
				'version': info.get('version'),
				'description': info.get('description'),
			},
			'statistics': {
				'total_paths': path_count,
				'total_endpoints': endpoint_count,
				'average_endpoints_per_path': endpoint_count / path_count
				if path_count > 0
				else 0,
			},
		}

	def _analyze_endpoints(self, spec: dict, include_details: bool) -> dict:
		"""分析端点信息"""
		paths = spec.get('paths', {})
		endpoints_by_method = {}
		endpoints_by_tag = {}

		for path, methods in paths.items():
			for method, details in methods.items():
				method_lower = method.lower()

				if method_lower not in endpoints_by_method:
					endpoints_by_method[method_lower] = 0
				endpoints_by_method[method_lower] += 1

				tags = details.get('tags', [])
				for tag in tags:
					if tag not in endpoints_by_tag:
						endpoints_by_tag[tag] = 0
					endpoints_by_tag[tag] += 1

		result = {
			'by_method': endpoints_by_method,
			'by_tag': endpoints_by_tag,
			'total': sum(endpoints_by_method.values()),
		}

		if include_details:
			result['detailed_endpoints'] = []
			for path, methods in paths.items():
				for method, details in methods.items():
					result['detailed_endpoints'].append(
						{
							'path': path,
							'method': method,
							'summary': details.get('summary', ''),
							'tags': details.get('tags', []),
						}
					)

		return result

	def _analyze_models(self, spec: dict, include_details: bool) -> dict:
		"""分析模型信息"""
		components = spec.get('components', {})
		schemas = components.get('schemas', {})

		model_stats = {
			'total_models': len(schemas),
			'model_types': {},
			'complexity_scores': {},
		}

		for model_name, model_def in schemas.items():
			# 分析模型类型
			model_type = model_def.get('type', 'object')
			if model_type not in model_stats['model_types']:
				model_stats['model_types'][model_type] = 0
			model_stats['model_types'][model_type] += 1

			# 计算复杂度分数
			complexity = self._calculate_model_complexity(model_def)
			model_stats['complexity_scores'][model_name] = complexity

		if include_details:
			model_stats['model_details'] = schemas

		return model_stats

	def _analyze_tags(self, spec: dict, include_details: bool) -> dict:
		"""分析标签信息"""
		tags = spec.get('tags', [])
		paths = spec.get('paths', {})

		tag_stats = {}
		for tag_info in tags:
			tag_name = tag_info.get('name')
			tag_stats[tag_name] = {
				'description': tag_info.get('description', ''),
				'endpoint_count': 0,
				'external_docs': tag_info.get('externalDocs', {}),
			}

		# 统计每个标签的端点数量
		for methods in paths.values():
			for details in methods.values():
				for tag in details.get('tags', []):
					if tag in tag_stats:
						tag_stats[tag]['endpoint_count'] += 1

		return {'total_tags': len(tags), 'tags': tag_stats}

	def _analyze_security(self, spec: dict, include_details: bool) -> dict:
		"""分析安全配置"""
		security_schemes = spec.get('components', {}).get('securitySchemes', {})
		global_security = spec.get('security', [])

		security_stats = {
			'total_security_schemes': len(security_schemes),
			'scheme_types': {},
			'global_security_requirements': len(global_security),
			'public_endpoints': 0,
			'secured_endpoints': 0,
		}

		for _scheme_name, scheme_def in security_schemes.items():
			scheme_type = scheme_def.get('type')
			if scheme_type not in security_stats['scheme_types']:
				security_stats['scheme_types'][scheme_type] = 0
			security_stats['scheme_types'][scheme_type] += 1

		# 统计安全端点
		paths = spec.get('paths', {})
		for methods in paths.values():
			for details in methods.values():
				if details.get('security'):
					security_stats['secured_endpoints'] += 1
				else:
					security_stats['public_endpoints'] += 1

		if include_details:
			security_stats['security_schemes'] = security_schemes
			security_stats['global_security'] = global_security

		return security_stats

	def _calculate_model_complexity(self, model_def: dict) -> int:
		"""计算模型复杂度分数"""
		score = 1

		if model_def.get('type') == 'object':
			properties = model_def.get('properties', {})
			score += len(properties) * 2

			for prop_def in properties.values():
				if '$ref' in prop_def:
					score += 3  # 引用增加复杂度
				elif prop_def.get('type') == 'array':
					score += 2  # 数组类型增加复杂度
				elif prop_def.get('type') == 'object':
					score += 4  # 嵌套对象显著增加复杂度

		return score


# 自定义工具2: 代码生成工具
class CodeGeneratorTool(BaseTool):
	"""代码生成工具 - 根据 OpenAPI 规范生成客户端代码"""

	def __init__(self):
		super().__init__()
		self.name = 'code_generator'
		self.description = '根据 OpenAPI 规范生成各种语言的客户端代码'

	def get_definition(self) -> ToolDefinition:
		"""获取工具定义"""
		return ToolDefinition(
			name=self.name,
			description=self.description,
			input_schema={
				'type': 'object',
				'properties': {
					'language': {
						'type': 'string',
						'enum': [
							'python',
							'javascript',
							'typescript',
							'java',
							'go',
							'curl',
						],
						'description': '目标编程语言',
						'default': 'python',
					},
					'output_format': {
						'type': 'string',
						'enum': ['classes', 'functions', 'sdk', 'examples'],
						'description': '输出格式',
						'default': 'functions',
					},
					'include_auth': {
						'type': 'boolean',
						'description': '是否包含认证代码',
						'default': True,
					},
					'filter_tags': {
						'type': 'array',
						'items': {'type': 'string'},
						'description': '只包含指定标签的端点（可选）',
					},
				},
				'required': ['language'],
			},
		)

	async def execute(self, arguments: dict[str, Any]) -> ToolResult:
		"""执行工具"""
		try:
			language = arguments['language']
			output_format = arguments.get('output_format', 'functions')
			include_auth = arguments.get('include_auth', True)
			filter_tags = arguments.get('filter_tags')

			# 获取 OpenAPI 规范
			spec = await self.get_openapi_spec()

			# 生成代码
			code = self._generate_code(
				spec, language, output_format, include_auth, filter_tags
			)

			return ToolResult(
				success=True,
				data={
					'language': language,
					'format': output_format,
					'code': code,
					'auth_included': include_auth,
				},
				message=f'{language.title()} 代码生成完成',
			)

		except Exception as e:
			return ToolResult(success=False, error=str(e), message='代码生成失败')

	def _generate_code(
		self,
		spec: dict,
		language: str,
		output_format: str,
		include_auth: bool,
		filter_tags: list[str] | None,
	) -> str:
		"""生成代码"""
		if language == 'python':
			return self._generate_python_code(
				spec, output_format, include_auth, filter_tags
			)
		elif language == 'javascript':
			return self._generate_javascript_code(
				spec, output_format, include_auth, filter_tags
			)
		elif language == 'typescript':
			return self._generate_typescript_code(
				spec, output_format, include_auth, filter_tags
			)
		elif language == 'curl':
			return self._generate_curl_examples(spec, filter_tags)
		else:
			raise ValueError(f'不支持的编程语言: {language}')

	def _generate_python_code(
		self,
		spec: dict,
		output_format: str,
		include_auth: bool,
		filter_tags: list[str] | None,
	) -> str:
		"""生成 Python 代码"""
		info = spec.get('info', {})
		title = info.get('title', 'API').replace(' ', '_').lower()
		base_url = spec.get('servers', [{}])[0].get('url', 'https://api.example.com')

		code = f'''"""
Auto-generated {info.get('title', 'API')} Python Client
Generated at: {datetime.now().isoformat()}
"""

import requests
import json
from typing import Dict, Any, Optional, List
'''

		if include_auth:
			code += '''
class Auth:
    """Authentication helper class"""

    def __init__(self, api_key: Optional[str] = None, bearer_token: Optional[str] = None):
        self.api_key = api_key
        self.bearer_token = bearer_token

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {{}}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {{self.bearer_token}}"
        return headers
'''

		code += f'''

class {title.title()}Client:
    """{info.get('title', 'API')} Client"""

    def __init__(self, base_url: str = "{base_url}", auth: Optional[Auth] = None):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{{self.base_url}}{{endpoint}}"

        headers = kwargs.get("headers", {{}})
        if self.auth:
            headers.update(self.auth.get_headers())
        kwargs["headers"] = headers

        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
'''

		# 添加端点方法
		paths = spec.get('paths', {})
		for path, methods in paths.items():
			for method, details in methods.items():
				if filter_tags and not any(
					tag in filter_tags for tag in details.get('tags', [])
				):
					continue

				method_name = self._generate_method_name(method, path, details)
				endpoint_path = self._convert_path_to_template(path)

				code += f'''
    def {method_name}(self{self._generate_method_params(path, details)}) -> Dict[str, Any]:
        """{details.get('summary', '')}"""
        params = locals()
        params.pop("self")

        # Remove None values
        params = {{k: v for k, v in params.items() if v is not None}}

        return self._make_request(
            "{method.upper()}",
            "{endpoint_path}"{self._generate_request_args(method, path)}
        )
'''

		return code

	def _generate_javascript_code(
		self,
		spec: dict,
		output_format: str,
		include_auth: bool,
		filter_tags: list[str] | None,
	) -> str:
		"""生成 JavaScript 代码"""
		info = spec.get('info', {})
		title = info.get('title', 'API').replace(' ', '_').lower()
		base_url = spec.get('servers', [{}])[0].get('url', 'https://api.example.com')

		code = f'''/**
 * Auto-generated {info.get('title', 'API')} JavaScript Client
 * Generated at: {datetime.now().isoformat()}
 */

class {title.title()}Client {{
    constructor(baseUrl = "{base_url}", apiKey = null) {{
        this.baseUrl = baseUrl.replace(/\\/$/, "");
        this.apiKey = apiKey;
    }}

    async _makeRequest(method, endpoint, options = {{}}) {{
        const url = `${{this.baseUrl}}${{endpoint}}`;

        const headers = {{
            "Content-Type": "application/json",
            ...options.headers
        }};

        if (this.apiKey) {{
            headers["X-API-Key"] = this.apiKey;
        }}

        const response = await fetch(url, {{
            method,
            headers,
            ...options
        }});

        if (!response.ok) {{
            throw new Error(`HTTP error! status: ${{response.status}}`);
        }}

        return await response.json();
    }}
'''

		# 添加端点方法
		paths = spec.get('paths', {})
		for path, methods in paths.items():
			for method, details in methods.items():
				if filter_tags and not any(
					tag in filter_tags for tag in details.get('tags', [])
				):
					continue

				method_name = self._generate_method_name(method, path, details)
				endpoint_path = self._convert_path_to_template(path)

				code += f'''
    async {method_name}({self._generate_js_method_params(path, details)}) {{
        const params = {{
            {self._generate_js_params_object(path, details)}
        }};

        // Remove undefined values
        Object.keys(params).forEach(key =>
            params[key] === undefined && delete params[key]
        );

        return await this._makeRequest(
            "{method.upper()}",
            "{endpoint_path}"{self._generate_js_request_args(method, path)}
        );
    }}
'''

		code += """
}
"""

		return code

	def _generate_curl_examples(
		self, spec: dict, filter_tags: list[str] | None
	) -> str:
		"""生成 cURL 示例"""
		info = spec.get('info', {})
		base_url = spec.get('servers', [{}])[0].get('url', 'https://api.example.com')

		code = f'''# {info.get('title', 'API')} cURL Examples
# Generated at: {datetime.now().isoformat()}

BASE_URL="{base_url}"
'''

		paths = spec.get('paths', {})
		for path, methods in paths.items():
			for method, details in methods.items():
				if filter_tags and not any(
					tag in filter_tags for tag in details.get('tags', [])
				):
					continue

				endpoint_path = self._convert_path_to_template(path)
				full_url = f'${{BASE_URL}}{endpoint_path}'

				code += f'''
# {details.get('summary', f'{method.upper()} {path}')}
curl -X {method.upper()} "{full_url}" \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json"
'''

		return code

	def _generate_method_name(self, method: str, path: str, details: dict) -> str:
		"""生成方法名"""
		# 移除路径参数
		clean_path = re.sub(r'\{[^}]+\}', '', path)
		# 移除前导斜杠并替换斜杠为下划线
		clean_path = clean_path.strip('/').replace('/', '_')
		# 移除多余的下划线
		clean_path = re.sub(r'_+', '_', clean_path)

		method_prefix = {
			'get': 'get',
			'post': 'create',
			'put': 'update',
			'patch': 'patch',
			'delete': 'delete',
		}.get(method.lower(), method.lower())

		if clean_path:
			return f'{method_prefix}_{clean_path}'
		else:
			return method_prefix

	def _convert_path_to_template(self, path: str) -> str:
		"""将路径转换为模板格式"""
		return re.sub(r'\{([^}]+)\}', r'{\1}', path)

	def _generate_method_params(self, path: str, details: dict) -> str:
		"""生成 Python 方法参数"""
		params = []

		# 路径参数
		path_params = re.findall(r'\{([^}]+)\}', path)
		for param in path_params:
			params.append(f'{param}: str')

		# 查询参数（简化处理）
		if details.get('parameters'):
			for param in details['parameters']:
				if param.get('in') == 'query':
					param_name = param['name']
					required = param.get('required', False)
					param_type = 'str'  # 简化处理
					default = '' if required else ' = None'
					params.append(f'{param_name}: {param_type}{default}')

		if not params:
			return ''

		return ', ' + ', '.join(params)

	def _generate_js_method_params(self, path: str, details: dict) -> str:
		"""生成 JavaScript 方法参数"""
		params = []

		# 路径参数
		path_params = re.findall(r'\{([^}]+)\}', path)
		for param in path_params:
			params.append(param)

		# 查询参数
		if details.get('parameters'):
			for param in details['parameters']:
				if param.get('in') == 'query':
					param_name = param['name']
					params.append(param_name)

		if not params:
			return ''

		return ', ' + ', '.join(params)

	def _generate_js_params_object(self, path: str, details: dict) -> str:
		"""生成 JavaScript 参数对象"""
		params = []

		# 路径参数
		path_params = re.findall(r'\{([^}]+)\}', path)
		for param in path_params:
			params.append(f'            {param}')

		# 查询参数
		if details.get('parameters'):
			for param in details['parameters']:
				if param.get('in') == 'query':
					param_name = param['name']
					params.append(f'            {param_name}')

		if not params:
			return '            // no parameters'

		return '\n'.join(params)

	def _generate_request_args(self, method: str, path: str) -> str:
		"""生成 Python 请求参数"""
		if method.upper() in ['POST', 'PUT', 'PATCH']:
			return ',\n            json=data'
		return ''

	def _generate_js_request_args(self, method: str, path: str) -> str:
		"""生成 JavaScript 请求参数"""
		if method.upper() in ['POST', 'PUT', 'PATCH']:
			return ',\n            body: JSON.stringify(data)'
		return ''

	def _generate_typescript_code(
		self,
		spec: dict,
		output_format: str,
		include_auth: bool,
		filter_tags: list[str] | None,
	) -> str:
		"""生成 TypeScript 代码（简化版本）"""
		# 基于JavaScript代码添加类型注解
		js_code = self._generate_javascript_code(
			spec, output_format, include_auth, filter_tags
		)

		# 添加类型定义
		types_code = """
// Type definitions
interface ApiResponse {
    [key: string]: any;
}

interface RequestOptions {
    headers?: Record<string, string>;
    body?: string;
}
"""

		return types_code + js_code.replace('class', 'class /* implements */').replace(
			'options = {}', 'options: RequestOptions = {}'
		)


# 自定义工具3: 测试数据生成工具
class TestDataGeneratorTool(BaseTool):
	"""测试数据生成工具 - 根据 OpenAPI 模型生成测试数据"""

	def __init__(self):
		super().__init__()
		self.name = 'test_data_generator'
		self.description = '根据 OpenAPI 模型定义生成测试数据'

	def get_definition(self) -> ToolDefinition:
		"""获取工具定义"""
		return ToolDefinition(
			name=self.name,
			description=self.description,
			input_schema={
				'type': 'object',
				'properties': {
					'model_name': {
						'type': 'string',
						'description': '模型名称（可选，如果不指定则生成所有模型的数据）',
					},
					'count': {
						'type': 'integer',
						'description': '生成数据条数',
						'default': 1,
						'minimum': 1,
						'maximum': 100,
					},
					'format': {
						'type': 'string',
						'enum': ['json', 'python', 'typescript'],
						'description': '输出格式',
						'default': 'json',
					},
					'locale': {
						'type': 'string',
						'description': '地区设置（影响生成的本地化数据）',
						'default': 'en',
					},
				},
			},
		)

	async def execute(self, arguments: dict[str, Any]) -> ToolResult:
		"""执行工具"""
		try:
			model_name = arguments.get('model_name')
			count = arguments.get('count', 1)
			format_type = arguments.get('format', 'json')
			locale = arguments.get('locale', 'en')

			# 获取 OpenAPI 规范
			spec = await self.get_openapi_spec()

			# 获取模型定义
			schemas = spec.get('components', {}).get('schemas', {})

			if model_name and model_name not in schemas:
				return ToolResult(
					success=False,
					error=f"模型 '{model_name}' 不存在",
					message='模型名称错误',
				)

			# 生成测试数据
			if model_name:
				test_data = self._generate_model_data(
					schemas[model_name], schemas, locale, count
				)
				result = {model_name: test_data}
			else:
				result = {}
				for name, model_def in schemas.items():
					result[name] = self._generate_model_data(
						model_def, schemas, locale, count
					)

			# 格式化输出
			if format_type == 'json':
				output = json.dumps(result, indent=2, ensure_ascii=False)
			elif format_type == 'python':
				output = self._format_as_python(result)
			elif format_type == 'typescript':
				output = self._format_as_typescript(result)
			else:
				raise ValueError(f'不支持的输出格式: {format_type}')

			return ToolResult(
				success=True,
				data={
					'format': format_type,
					'locale': locale,
					'count': count,
					'data': output,
				},
				message='测试数据生成完成',
			)

		except Exception as e:
			return ToolResult(success=False, error=str(e), message='测试数据生成失败')

	def _generate_model_data(
		self, model_def: dict, all_schemas: dict, locale: str, count: int
	) -> list[dict]:
		"""为模型生成测试数据"""
		data_list = []

		for _ in range(count):
			data = self._generate_value_for_schema(model_def, all_schemas, locale)
			data_list.append(data)

		return data_list

	def _generate_value_for_schema(
		self, schema: dict, all_schemas: dict, locale: str
	) -> Any:
		"""根据 schema 生成值"""
		if '$ref' in schema:
			# 处理引用
			ref_path = schema['$ref']
			if ref_path.startswith('#/components/schemas/'):
				model_name = ref_path.split('/')[-1]
				if model_name in all_schemas:
					return self._generate_value_for_schema(
						all_schemas[model_name], all_schemas, locale
					)

		schema_type = schema.get('type', 'string')

		if schema_type == 'object':
			obj = {}
			properties = schema.get('properties', {})
			for prop_name, prop_schema in properties.items():
				obj[prop_name] = self._generate_value_for_schema(
					prop_schema, all_schemas, locale
				)
			return obj

		elif schema_type == 'array':
			items_schema = schema.get('items', {'type': 'string'})
			# 生成1-3个数组元素
			array_length = min(3, max(1, schema.get('minItems', 1)))
			return [
				self._generate_value_for_schema(items_schema, all_schemas, locale)
				for _ in range(array_length)
			]

		elif schema_type == 'string':
			return self._generate_string_value(schema, locale)

		elif schema_type == 'integer':
			return self._generate_integer_value(schema)

		elif schema_type == 'number':
			return self._generate_number_value(schema)

		elif schema_type == 'boolean':
			return True

		else:
			return 'generated_value'

	def _generate_string_value(self, schema: dict, locale: str) -> str:
		"""生成字符串值"""
		format_type = schema.get('format')

		if format_type == 'email':
			return f'user{hash(locale) % 1000}@example.com'
		elif format_type == 'date':
			return '2024-01-15'
		elif format_type == 'date-time':
			return '2024-01-15T10:30:00Z'
		elif format_type == 'uuid':
			return '550e8400-e29b-41d4-a716-446655440000'
		elif schema.get('enum'):
			return schema['enum'][0]
		else:
			# 根据字段名生成合适的值
			min_length = schema.get('minLength', 1)
			max_length = min(schema.get('maxLength', 20), 50)
			length = min(max_length, max(min_length, 5))

			field_name = 'value'  # 这里可以根据上下文推断字段名
			if 'name' in field_name.lower():
				return self._generate_name(locale, length)
			elif 'email' in field_name.lower():
				return f'test{length}@example.com'
			elif 'description' in field_name.lower() or 'content' in field_name.lower():
				return 'This is a generated description for testing purposes.'
			else:
				return 'x' * length

	def _generate_integer_value(self, schema: dict) -> int:
		"""生成整数值"""
		minimum = schema.get('minimum', 0)
		maximum = schema.get('maximum', 100)

		if 'enum' in schema:
			return schema['enum'][0]

		return min(
			maximum, max(minimum, minimum + (hash('test') % (maximum - minimum + 1)))
		)

	def _generate_number_value(self, schema: dict) -> float:
		"""生成数字值"""
		minimum = schema.get('minimum', 0.0)
		maximum = schema.get('maximum', 100.0)

		return round(minimum + (hash('test') % 100) / 100 * (maximum - minimum), 2)

	def _generate_name(self, locale: str, length: int) -> str:
		"""生成姓名"""
		names = {
			'en': ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana'],
			'zh': ['张三', '李四', '王五', '赵六', '孙七', '周八'],
			'ja': ['田中', '佐藤', '鈴木', '高橋', '伊藤'],
		}

		name_list = names.get(locale, names['en'])
		name = name_list[hash('test') % len(name_list)]

		return name[:length]

	def _format_as_python(self, data: dict) -> str:
		"""格式化为 Python 代码"""
		output = '# Generated test data\n\n'

		for model_name, values in data.items():
			class_name = self._to_pascal_case(model_name)
			output += f'class {class_name}:\n'

			if values:
				first_value = values[0]
				for key, value in first_value.items():
					value_repr = repr(value)
					output += f'    {key} = {value_repr}\n'

				output += f'\n# Test instances\n{model_name.lower()}_data = [\n'
				for value in values:
					output += f'    {class_name}(**{repr(value)}),\n'
				output += ']\n\n'

		return output

	def _format_as_typescript(self, data: dict) -> str:
		"""格式化为 TypeScript 代码"""
		output = '// Generated test data\n\n'

		# 生成接口定义
		for model_name, values in data.items():
			interface_name = self._to_pascal_case(model_name)
			output += f'interface {interface_name} {{\n'

			if values:
				first_value = values[0]
				for key, value in first_value.items():
					type_str = self._infer_typescript_type(value)
					output += f'  {key}: {type_str};\n'

			output += '}\n\n'

		# 生成测试数据
		for model_name, values in data.items():
			output += f'const {model_name.toLowerCase()}TestData: {self._to_pascal_case(model_name)}[] = [\n'
			for value in values:
				output += f'  {json.dumps(value, ensure_ascii=False)},\n'
			output += '];\n\n'

		return output

	def _to_pascal_case(self, snake_str: str) -> str:
		"""转换为 PascalCase"""
		return ''.join(word.capitalize() for word in snake_str.split('_'))

	def _infer_typescript_type(self, value: Any) -> str:
		"""推断 TypeScript 类型"""
		if isinstance(value, str):
			return 'string'
		elif isinstance(value, int):
			return 'number'
		elif isinstance(value, float):
			return 'number'
		elif isinstance(value, bool):
			return 'boolean'
		elif isinstance(value, list):
			if value:
				item_type = self._infer_typescript_type(value[0])
				return f'{item_type}[]'
			return 'any[]'
		elif isinstance(value, dict):
			return 'Record<string, any>'
		else:
			return 'any'


# 自定义工具4: 性能分析工具
class PerformanceAnalyzerTool(BaseTool):
	"""性能分析工具 - 分析 API 性能指标"""

	def __init__(self):
		super().__init__()
		self.name = 'performance_analyzer'
		self.description = '分析 OpenAPI 规范，评估 API 性能特征和优化建议'

	def get_definition(self) -> ToolDefinition:
		"""获取工具定义"""
		return ToolDefinition(
			name=self.name,
			description=self.description,
			input_schema={
				'type': 'object',
				'properties': {
					'analysis_type': {
						'type': 'string',
						'enum': [
							'complexity',
							'optimization',
							'bottlenecks',
							'recommendations',
						],
						'description': '分析类型',
						'default': 'recommendations',
					},
					'traffic_profile': {
						'type': 'string',
						'enum': ['low', 'medium', 'high', 'enterprise'],
						'description': '预期流量级别',
						'default': 'medium',
					},
				},
			},
		)

	async def execute(self, arguments: dict[str, Any]) -> ToolResult:
		"""执行工具"""
		try:
			analysis_type = arguments.get('analysis_type', 'recommendations')
			traffic_profile = arguments.get('traffic_profile', 'medium')

			# 获取 OpenAPI 规范
			spec = await self.get_openapi_spec()

			# 执行性能分析
			result = self._analyze_performance(spec, analysis_type, traffic_profile)

			return ToolResult(
				success=True, data=result, message=f'性能分析完成: {analysis_type}'
			)

		except Exception as e:
			return ToolResult(success=False, error=str(e), message='性能分析失败')

	def _analyze_performance(
		self, spec: dict, analysis_type: str, traffic_profile: str
	) -> dict:
		"""分析性能"""
		if analysis_type == 'complexity':
			return self._analyze_complexity(spec)
		elif analysis_type == 'optimization':
			return self._analyze_optimization_opportunities(spec)
		elif analysis_type == 'bottlenecks':
			return self._identify_potential_bottlenecks(spec, traffic_profile)
		elif analysis_type == 'recommendations':
			return self._generate_recommendations(spec, traffic_profile)
		else:
			raise ValueError(f'未知的分析类型: {analysis_type}')

	def _analyze_complexity(self, spec: dict) -> dict:
		"""分析 API 复杂度"""
		paths = spec.get('paths', {})

		complexity_scores = []
		for path, methods in paths.items():
			for method, details in methods.items():
				score = self._calculate_endpoint_complexity(path, details)
				complexity_scores.append(
					{
						'endpoint': f'{method.upper()} {path}',
						'score': score,
						'factors': self._get_complexity_factors(details),
					}
				)

		# 按复杂度排序
		complexity_scores.sort(key=lambda x: x['score'], reverse=True)

		return {
			'average_complexity': sum(s['score'] for s in complexity_scores)
			/ len(complexity_scores),
			'most_complex': complexity_scores[:5],
			'least_complex': complexity_scores[-5:],
			'total_endpoints': len(complexity_scores),
		}

	def _analyze_optimization_opportunities(self, spec: dict) -> dict:
		"""分析优化机会"""
		opportunities = []

		paths = spec.get('paths', {})
		for path, methods in paths.items():
			for method, details in methods.items():
				endpoint = f'{method.upper()} {path}'

				# 检查缓存机会
				if method.upper() == 'GET' and not self._has_cache_headers(details):
					opportunities.append(
						{
							'type': 'caching',
							'endpoint': endpoint,
							'suggestion': '添加缓存头以提高 GET 请求性能',
							'impact': 'high',
						}
					)

				# 检查分页机会
				if (
					method.upper() == 'GET'
					and 'list' in path
					and not self._has_pagination(details)
				):
					opportunities.append(
						{
							'type': 'pagination',
							'endpoint': endpoint,
							'suggestion': '添加分页参数以处理大数据集',
							'impact': 'medium',
						}
					)

				# 检查数据压缩机会
				if not self._has_compression(details):
					opportunities.append(
						{
							'type': 'compression',
							'endpoint': endpoint,
							'suggestion': '启用响应压缩以减少带宽使用',
							'impact': 'medium',
						}
					)

		return {
			'total_opportunities': len(opportunities),
			'opportunities': sorted(
				opportunities, key=lambda x: x['impact'], reverse=True
			),
		}

	def _identify_potential_bottlenecks(self, spec: dict, traffic_profile: str) -> dict:
		"""识别潜在瓶颈"""
		bottlenecks = []

		paths = spec.get('paths', {})
		for path, methods in paths.items():
			for method, details in methods.items():
				endpoint = f'{method.upper()} {path}'

				# 检查复杂查询参数
				complex_params = self._get_complex_parameters(details)
				if complex_params:
					bottlenecks.append(
						{
							'type': 'complex_parameters',
							'endpoint': endpoint,
							'description': f'复杂参数可能影响性能: {", ".join(complex_params)}',
							'severity': 'medium',
						}
					)

				# 检查大响应潜力
				if self._has_large_response_potential(details):
					bottlenecks.append(
						{
							'type': 'large_response',
							'endpoint': endpoint,
							'description': '可能返回大量数据，影响响应时间',
							'severity': 'high',
						}
					)

				# 检查缺少限制的端点
				if not self._has_rate_limiting_hints(details):
					bottlenecks.append(
						{
							'type': 'no_rate_limiting',
							'endpoint': endpoint,
							'description': '缺少速率限制提示，可能在流量高峰时出现问题',
							'severity': 'medium',
						}
					)

		return {
			'traffic_profile': traffic_profile,
			'total_bottlenecks': len(bottlenecks),
			'bottlenecks': bottlenecks,
		}

	def _generate_recommendations(self, spec: dict, traffic_profile: str) -> dict:
		"""生成性能优化建议"""
		recommendations = []

		# 基础建议
		recommendations.extend(
			[
				{
					'category': 'caching',
					'priority': 'high',
					'recommendation': '为所有 GET 端点实现适当的缓存策略',
					'implementation': '使用 HTTP 缓存头或 Redis 缓存',
				},
				{
					'category': 'monitoring',
					'priority': 'high',
					'recommendation': '实现全面的性能监控',
					'implementation': '监控响应时间、错误率、吞吐量等关键指标',
				},
			]
		)

		# 基于流量级别的建议
		if traffic_profile in ['high', 'enterprise']:
			recommendations.extend(
				[
					{
						'category': 'scaling',
						'priority': 'critical',
						'recommendation': '实现水平扩展能力',
						'implementation': '使用负载均衡器和自动扩缩容',
					},
					{
						'category': 'database',
						'priority': 'high',
						'recommendation': '优化数据库查询和连接池',
						'implementation': '添加索引、使用读写分离、优化连接池配置',
					},
				]
			)

		# 基于分析的具体建议
		paths = spec.get('paths', {})
		total_endpoints = sum(len(methods) for methods in paths.values())

		if total_endpoints > 50:
			recommendations.append(
				{
					'category': 'architecture',
					'priority': 'medium',
					'recommendation': '考虑 API 拆分为微服务',
					'implementation': '按业务功能拆分大型 API',
				}
			)

		return {
			'traffic_profile': traffic_profile,
			'total_recommendations': len(recommendations),
			'recommendations': sorted(
				recommendations,
				key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}[x['priority']],
			),
		}

	def _calculate_endpoint_complexity(self, path: str, details: dict) -> int:
		"""计算端点复杂度"""
		score = 1

		# 路径复杂度
		path_params = len(re.findall(r'\{[^}]+\}', path))
		score += path_params * 2

		# 参数复杂度
		parameters = details.get('parameters', [])
		score += len(parameters)

		# 响应复杂度
		responses = details.get('responses', {})
		for response in responses.values():
			content = response.get('content', {})
			if 'application/json' in content:
				score += 3  # JSON 响应增加复杂度

		return score

	def _get_complexity_factors(self, details: dict) -> list[str]:
		"""获取复杂度因素"""
		factors = []

		if len(details.get('parameters', [])) > 5:
			factors.append('多个参数')

		if len(re.findall(r'\{[^}]+\}', details.get('path', ''))) > 2:
			factors.append('多个路径参数')

		if len(details.get('responses', {})) > 3:
			factors.append('多个响应类型')

		return factors

	def _has_cache_headers(self, details: dict) -> bool:
		"""检查是否有缓存头"""
		# 简化检查，实际中需要检查响应头定义
		return 'cache' in str(details).lower()

	def _has_pagination(self, details: dict) -> bool:
		"""检查是否有分页"""
		params = details.get('parameters', [])
		pagination_params = ['limit', 'offset', 'page', 'size', 'skip']
		return any(p.get('name') in pagination_params for p in params)

	def _has_compression(self, details: dict) -> bool:
		"""检查是否支持压缩"""
		return 'compression' in str(details).lower()

	def _get_complex_parameters(self, details: dict) -> list[str]:
		"""获取复杂参数"""
		complex_params = []
		for param in details.get('parameters', []):
			if param.get('type') == 'array' or param.get('type') == 'object':
				complex_params.append(param.get('name', ''))
		return complex_params

	def _has_large_response_potential(self, details: dict) -> bool:
		"""检查是否有大响应潜力"""
		responses = details.get('responses', {})
		for response in responses.values():
			content = response.get('content', {})
			if 'application/json' in content:
				schema = content['application/json'].get('schema', {})
				if schema.get('type') == 'array':
					return True
		return False

	def _has_rate_limiting_hints(self, details: dict) -> bool:
		"""检查是否有速率限制提示"""
		return 'rate' in str(details).lower() or 'limit' in str(details).lower()


# 自定义工具注册和演示
def main():
	"""运行自定义工具演示"""
	print('🔧 OpenAPI MCP 自定义工具演示')
	print('=' * 60)

	# 创建演示应用
	app = create_demo_app()

	# 创建 MCP 服务器
	mcp_server = OpenApiMcpServer(app)

	# 注册自定义工具
	custom_tools = [
		ApiAnalyzerTool(),
		CodeGeneratorTool(),
		TestDataGeneratorTool(),
		PerformanceAnalyzerTool(),
	]

	for tool in custom_tools:
		mcp_server.register_tool(tool)
		print(f'✅ 注册自定义工具: {tool.name}')

	# 挂载 MCP 服务器
	mcp_server.mount('/mcp')

	print('\n📋 已注册的自定义工具:')
	for tool in custom_tools:
		definition = tool.get_definition()
		print(f'  🔧 {tool.name}')
		print(f'     描述: {definition.description}')
		print(f'     参数: {len(definition.input_schema.get("properties", {}))} 个')

	print('\n💡 自定义工具功能:')
	print('  1. API 分析器 - 深入分析 OpenAPI 规范')
	print('  2. 代码生成器 - 生成多语言客户端代码')
	print('  3. 测试数据生成器 - 自动生成测试数据')
	print('  4. 性能分析器 - 评估和优化 API 性能')

	print('\n🚀 使用方法:')
	print('  1. 启动服务器: python custom_tool_example.py')
	print('  2. 连接 MCP 客户端到 http://localhost:8000/mcp')
	print('  3. 调用自定义工具进行相应操作')

	print('\n📖 扩展自定义工具:')
	print('  - 继承 BaseTool 基类')
	print('  - 实现 get_definition() 方法定义工具接口')
	print('  - 实现 execute() 方法提供工具功能')
	print('  - 使用 register_tool() 注册到服务器')

	return app


if __name__ == '__main__':
	import uvicorn

	app = main()

	print('\n🌐 启动服务器...')
	print('   访问 http://localhost:8000/docs 查看 API 文档')
	print('   连接 http://localhost:8000/mcp 使用自定义工具')

	uvicorn.run(app, host='0.0.0.0', port=8000)
