"""
Models Resources

提供数据模型相关的 Resources。
"""

import json
from typing import Any, ClassVar

from openapi_mcp.resources.base import BaseResource


class ModelsListResource(BaseResource):
	"""模型列表 Resource

	URI: openapi://models
	提供所有数据模型的概要信息。

	Attributes:
	    uri_template: URI 模板 'openapi://models'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://models'
	name: ClassVar[str] = 'API Models List'
	description: ClassVar[str] = '所有数据模型的概要信息列表'

	async def read(self, uri: str) -> str:
		"""读取模型列表

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的模型列表字符串

		Raises:
		    ValueError: 当 URI 不匹配时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		try:
			spec = await self.get_openapi_spec()
			models = self._extract_models(spec)
			return json.dumps(models, indent=2, ensure_ascii=False)
		except Exception as e:
			raise RuntimeError(f'无法获取模型列表: {e}') from e

	def _extract_models(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
		"""从 OpenAPI spec 中提取模型信息

		Args:
		    spec: OpenAPI specification

		Returns:
		    模型信息列表
		"""
		models = []
		schemas = spec.get('components', {}).get('schemas', {})

		for name, schema in schemas.items():
			model = {
				'name': name,
				'type': schema.get('type', 'object'),
				'description': schema.get('description', ''),
				'properties': list(schema.get('properties', {}).keys()),
				'required': schema.get('required', []),
			}
			models.append(model)

		return models


class ModelResource(BaseResource):
	"""具体模型 Resource

	URI: openapi://models/{name}
	提供特定模型的完整定义。

	Attributes:
	    uri_template: URI 模板 'openapi://models/{name}'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://models/{name}'
	name: ClassVar[str] = 'API Model Details'
	description: ClassVar[str] = '特定数据模型的完整定义'

	async def read(self, uri: str) -> str:
		"""读取模型详情

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的模型详情字符串

		Raises:
		    ValueError: 当 URI 不匹配或模型不存在时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		params = self.extract_params(uri)
		name = params.get('name', '')

		if not name:
			raise ValueError('模型名称参数不能为空')

		try:
			spec = await self.get_openapi_spec()
			model = self._extract_model(spec, name)

			if not model:
				raise ValueError(f'模型不存在: {name}')

			return json.dumps(model, indent=2, ensure_ascii=False)
		except Exception as e:
			if isinstance(e, (ValueError, RuntimeError)):
				raise
			raise RuntimeError(f'无法获取模型详情: {e}') from e

	def _extract_model(self, spec: dict[str, Any], name: str) -> dict[str, Any] | None:
		"""从 OpenAPI spec 中提取特定模型信息

		Args:
		    spec: OpenAPI specification
		    name: 模型名称

		Returns:
		    模型完整定义，如果不存在返回 None
		"""
		schemas = spec.get('components', {}).get('schemas', {})
		return schemas.get(name)
