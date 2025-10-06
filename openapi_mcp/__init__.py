"""
FastAPI OpenAPI MCP Server

将 FastAPI 应用的 OpenAPI 文档转换为 MCP Tools，
让 AI 编程助手能够高效查询 API 信息，减少 Token 消耗。
"""

__version__ = '0.1.0'
__author__ = 'Your Name'
__license__ = 'MIT'

# 主要导出的类和函数
from openapi_mcp.config import OpenApiMcpConfig
from openapi_mcp.server import OpenApiMcpServer
from openapi_mcp.tools.base import BaseMcpTool

__all__ = [
	'__version__',
	'OpenApiMcpServer',
	'OpenApiMcpConfig',
	'BaseMcpTool',
]
