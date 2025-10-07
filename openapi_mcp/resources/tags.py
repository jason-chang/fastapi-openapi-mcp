"""
Tags Resources

提供标签相关的 Resources。
"""

import json
from typing import Any, ClassVar

from openapi_mcp.resources.base import BaseResource


class TagsListResource(BaseResource):
	"""标签列表 Resource

	URI: openapi://tags
	提供所有标签及统计信息。

	Attributes:
	    uri_template: URI 模板 'openapi://tags'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://tags'
	name: ClassVar[str] = 'API Tags List'
	description: ClassVar[str] = '所有标签及统计信息'

	async def read(self, uri: str) -> str:
		"""读取标签列表

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的标签列表字符串

		Raises:
		    ValueError: 当 URI 不匹配时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		try:
			spec = await self.get_openapi_spec()
			tags = self._extract_tags(spec)
			return json.dumps(tags, indent=2, ensure_ascii=False)
		except Exception as e:
			raise RuntimeError(f'无法获取标签列表: {e}') from e

	def _extract_tags(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
		"""从 OpenAPI spec 中提取标签信息

		Args:
		    spec: OpenAPI specification

		Returns:
		    标签信息列表
		"""
		# 获取标签定义
		tag_definitions = {tag['name']: tag for tag in spec.get('tags', [])}

		# 统计每个标签的端点数量
		tag_counts = {}
		paths = spec.get('paths', {})

		for _path, path_item in paths.items():
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
					operation_tags = operation.get('tags', ['default'])
					for tag in operation_tags:
						tag_counts[tag] = tag_counts.get(tag, 0) + 1

		# 构建标签信息
		tags = []
		for tag_name, count in tag_counts.items():
			tag_info = {
				'name': tag_name,
				'endpoints_count': count,
			}

			# 如果有标签定义，添加描述等信息
			if tag_name in tag_definitions:
				tag_def = tag_definitions[tag_name]
				tag_info['description'] = tag_def.get('description', '')

			tags.append(tag_info)

		# 按名称排序
		tags.sort(key=lambda x: x['name'])

		return tags


class TagEndpointsResource(BaseResource):
	"""标签端点 Resource

	URI: openapi://tags/{tag}/endpoints
	提供特定标签下的所有端点。

	Attributes:
	    uri_template: URI 模板 'openapi://tags/{tag}/endpoints'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://tags/{tag}/endpoints'
	name: ClassVar[str] = 'Tag Endpoints List'
	description: ClassVar[str] = '特定标签下的所有端点列表'

	async def read(self, uri: str) -> str:
		"""读取标签端点列表

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的端点列表字符串

		Raises:
		    ValueError: 当 URI 不匹配或标签不存在时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		params = self.extract_params(uri)
		tag = params.get('tag', '')

		if not tag:
			raise ValueError('标签参数不能为空')

		try:
			spec = await self.get_openapi_spec()
			endpoints = self._extract_tag_endpoints(spec, tag)
			return json.dumps(endpoints, indent=2, ensure_ascii=False)
		except Exception as e:
			if isinstance(e, (ValueError, RuntimeError)):
				raise
			raise RuntimeError(f'无法获取标签端点: {e}') from e

	def _extract_tag_endpoints(
		self, spec: dict[str, Any], tag: str
	) -> list[dict[str, Any]]:
		"""从 OpenAPI spec 中提取特定标签的端点信息

		Args:
		    spec: OpenAPI specification
		    tag: 标签名称

		Returns:
		    端点信息列表
		"""
		endpoints = []
		paths = spec.get('paths', {})

		for path, path_item in paths.items():
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
					operation_tags = operation.get('tags', ['default'])
					if tag in operation_tags:
						endpoint = {
							'path': path,
							'method': method.upper(),
							'operationId': operation.get('operationId'),
							'summary': operation.get('summary', ''),
							'description': operation.get('description', ''),
						}
						endpoints.append(endpoint)

		return endpoints
