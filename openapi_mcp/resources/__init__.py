"""
MCP Resources 模块

基于 MCP 2025-06-18 标准的 Resources 实现，
提供对 OpenAPI 文档的结构化访问。
"""

from openapi_mcp.resources.base import BaseResource
from openapi_mcp.resources.endpoints import EndpointResource, EndpointsListResource
from openapi_mcp.resources.manager import ResourceManager
from openapi_mcp.resources.models import ModelResource, ModelsListResource
from openapi_mcp.resources.spec import OpenApiSpecResource
from openapi_mcp.resources.tags import TagEndpointsResource, TagsListResource

__all__ = [
	'BaseResource',
	'ResourceManager',
	'OpenApiSpecResource',
	'EndpointsListResource',
	'EndpointResource',
	'ModelsListResource',
	'ModelResource',
	'TagsListResource',
	'TagEndpointsResource',
]
