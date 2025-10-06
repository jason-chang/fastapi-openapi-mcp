"""
Endpoints Resources

提供 API 端点相关的 Resources。
"""

import json
from typing import Any, ClassVar

from openapi_mcp.resources.base import BaseResource


class EndpointsListResource(BaseResource):
	"""端点列表 Resource

	URI: openapi://endpoints
	提供所有 API 端点的概要信息。

	Attributes:
	    uri_template: URI 模板 'openapi://endpoints'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://endpoints'
	name: ClassVar[str] = 'API Endpoints List'
	description: ClassVar[str] = '所有 API 端点的概要信息列表'

	async def read(self, uri: str) -> str:
		"""读取端点列表

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的端点列表字符串

		Raises:
		    ValueError: 当 URI 不匹配时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		try:
			spec = await self.get_openapi_spec()
			endpoints = self._extract_endpoints(spec)
			return json.dumps(endpoints, indent=2, ensure_ascii=False)
		except Exception as e:
			raise RuntimeError(f'无法获取端点列表: {e}') from e

	def _extract_endpoints(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
		"""从 OpenAPI spec 中提取端点信息

		Args:
		    spec: OpenAPI specification

		Returns:
		    端点信息列表
		"""
		endpoints = []
		paths = spec.get('paths', {})

		for path, path_item in paths.items():
			if not isinstance(path_item, dict):
				continue

			for method, operation in path_item.items():
				if method.upper() in [
					'GET',
					'POST',
					'PUT',
					'DELETE',
					'PATCH',
					'HEAD',
					'OPTIONS',
				] and isinstance(operation, dict):
					endpoint = {
						'path': path,
						'method': method.upper(),
						'operationId': operation.get('operationId'),
						'summary': operation.get('summary', ''),
						'description': operation.get('description', ''),
						'tags': operation.get('tags', []),
					}
					endpoints.append(endpoint)

		return endpoints


class EndpointResource(BaseResource):
	"""具体端点 Resource

	URI: openapi://endpoints/{path}
	提供特定端点的详细信息。

	Attributes:
	    uri_template: URI 模板 'openapi://endpoints/{path}'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://endpoints/{path}'
	name: ClassVar[str] = 'API Endpoint Details'
	description: ClassVar[str] = '特定 API 端点的详细信息'

	async def read(self, uri: str) -> str:
		"""读取端点详情

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的端点详情字符串

		Raises:
		    ValueError: 当 URI 不匹配或端点不存在时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		params = self.extract_params(uri)
		path = params.get('path', '')

		if not path:
			raise ValueError('路径参数不能为空')

		# 确保路径以 / 开头
		if not path.startswith('/'):
			path = '/' + path

		try:
			spec = await self.get_openapi_spec()
			endpoint = self._extract_endpoint(spec, path)

			if not endpoint:
				raise ValueError(f'端点不存在: {path}')

			return json.dumps(endpoint, indent=2, ensure_ascii=False)
		except Exception as e:
			if isinstance(e, (ValueError, RuntimeError)):
				raise
			raise RuntimeError(f'无法获取端点详情: {e}') from e

	def _extract_endpoint(
		self, spec: dict[str, Any], path: str
	) -> dict[str, Any] | None:
		"""从 OpenAPI spec 中提取特定端点信息

		Args:
		    spec: OpenAPI specification
		    path: 端点路径

		Returns:
		    端点详细信息，如果不存在返回 None
		"""
		paths = spec.get('paths', {})
		path_item = paths.get(path)

		if not path_item:
			return None

		# 构建端点详细信息
		endpoint = {
			'path': path,
			'methods': {},
			'parameters': path_item.get('parameters', []),
		}

		for method, operation in path_item.items():
			if method.upper() in [
				'GET',
				'POST',
				'PUT',
				'DELETE',
				'PATCH',
				'HEAD',
				'OPTIONS',
			]:
				endpoint['methods'][method.upper()] = {
					'operationId': operation.get('operationId'),
					'summary': operation.get('summary', ''),
					'description': operation.get('description', ''),
					'tags': operation.get('tags', []),
					'parameters': operation.get('parameters', []),
					'requestBody': operation.get('requestBody'),
					'responses': operation.get('responses', {}),
					'security': operation.get('security'),
				}

		return endpoint
