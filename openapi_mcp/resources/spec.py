"""
OpenAPI Spec Resource

提供完整的 OpenAPI specification 访问。
"""

import json
from typing import ClassVar

from openapi_mcp.resources.base import BaseResource


class OpenApiSpecResource(BaseResource):
	"""OpenAPI Specification Resource

	URI: openapi://spec
	提供完整的 OpenAPI specification 文档。

	Attributes:
	    uri_template: URI 模板 'openapi://spec'
	    name: Resource 名称
	    description: Resource 描述
	"""

	uri_template: ClassVar[str] = 'openapi://spec'
	name: ClassVar[str] = 'OpenAPI Specification'
	description: ClassVar[str] = '完整的 OpenAPI specification 文档'

	async def read(self, uri: str) -> str:
		"""读取 OpenAPI spec

		Args:
		    uri: 请求的 URI

		Returns:
		    JSON 格式的 OpenAPI spec 字符串

		Raises:
		    ValueError: 当 URI 不匹配时
		    RuntimeError: 当无法获取 OpenAPI spec 时
		"""
		if not self.matches_uri(uri):
			raise ValueError(f'URI {uri} 不匹配模板 {self.uri_template}')

		try:
			spec = await self.get_openapi_spec()
			return json.dumps(spec, indent=2, ensure_ascii=False)
		except Exception as e:
			raise RuntimeError(f'无法获取 OpenAPI spec: {e}') from e
