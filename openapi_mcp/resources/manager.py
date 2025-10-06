"""
Resource 管理器

管理所有 Resource 实例，处理 URI 路由和资源发现。
"""

from mcp.types import Resource, TextContent

from openapi_mcp.resources.base import BaseResource


class ResourceManager:
	"""Resource 管理器

	负责 Resource 的注册、路由和管理，符合 MCP 2025-06-18 标准。

	Attributes:
	    resources: 已注册的 Resource 列表
	    resource_map: URI 模板到 Resource 的映射
	"""

	def __init__(self) -> None:
		"""初始化 Resource 管理器"""
		self.resources: list[BaseResource] = []
		self.resource_map: dict[str, BaseResource] = {}

	def register_resource(self, resource: BaseResource) -> None:
		"""注册 Resource

		Args:
		    resource: 要注册的 Resource 实例

		Raises:
		    ValueError: 当 URI 模板重复时
		"""
		if resource.uri_template in self.resource_map:
			raise ValueError(f'URI 模板重复: {resource.uri_template}')

		self.resources.append(resource)
		self.resource_map[resource.uri_template] = resource

	def list_resources(self) -> list[Resource]:
		"""列出所有可用的 Resources

		Returns:
		    Resource 信息列表
		"""
		return [resource.to_resource_info() for resource in self.resources]

	async def read_resource(self, uri: str) -> list[TextContent]:
		"""读取 Resource 内容

		Args:
		    uri: 请求的 URI

		Returns:
		    包含 Resource 内容的 TextContent 列表

		Raises:
		    ValueError: 当找不到匹配的 Resource 时
		    RuntimeError: 当读取 Resource 失败时
		"""
		# 查找匹配的 Resource
		for resource in self.resources:
			if resource.matches_uri(uri):
				try:
					content = await resource.read(uri)
					return [resource.create_text_content(content)]
				except Exception as e:
					raise RuntimeError(f'读取 Resource 失败: {e}') from e

		raise ValueError(f'找不到匹配的 Resource: {uri}')

	def get_resource_by_uri(self, uri: str) -> BaseResource | None:
		"""根据 URI 获取 Resource

		Args:
		    uri: URI

		Returns:
		    匹配的 Resource 实例，如果不存在返回 None
		"""
		for resource in self.resources:
			if resource.matches_uri(uri):
				return resource
		return None

	def clear_resources(self) -> None:
		"""清除所有已注册的 Resources"""
		self.resources.clear()
		self.resource_map.clear()

	def get_resource_count(self) -> int:
		"""获取已注册的 Resource 数量

		Returns:
		    Resource 数量
		"""
		return len(self.resources)
