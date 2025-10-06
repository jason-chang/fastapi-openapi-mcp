"""
MCP Streamable HTTP 传输层

符合 MCP 2025-06-18 标准的 HTTP 传输实现。
支持单个端点同时处理 POST 和 GET 请求，实现 JSON-RPC 和 SSE 通信。
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from openapi_mcp.resources.manager import ResourceManager
from openapi_mcp.security import AccessLogger, SensitiveDataMasker, ToolFilter
from openapi_mcp.tools.base import BaseMcpTool

# 设置日志记录器
logger = logging.getLogger(__name__)

# MCP 协议版本
MCP_PROTOCOL_VERSION = '2025-06-18'

# 会话过期时间（秒）
SESSION_TIMEOUT = 3600  # 1 小时


class McpSession:
	"""MCP 会话管理

	管理客户端与服务器之间的会话状态。

	Attributes:
		session_id: 会话唯一标识
		created_at: 会话创建时间
		last_activity: 最后活动时间
		initialized: 是否已完成初始化
		message_queue: 待发送的消息队列（用于 SSE）
		capabilities: 服务器能力
	"""

	def __init__(self, session_id: str) -> None:
		"""初始化会话

		Args:
			session_id: 会话唯一标识
		"""
		self.session_id = session_id
		self.created_at = datetime.now()
		self.last_activity = datetime.now()
		self.initialized = False
		self.message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
		self.capabilities: dict[str, Any] = {}

	def is_expired(self) -> bool:
		"""检查会话是否过期

		Returns:
			True 表示会话已过期
		"""
		return datetime.now() - self.last_activity > timedelta(seconds=SESSION_TIMEOUT)

	def update_activity(self) -> None:
		"""更新最后活动时间"""
		self.last_activity = datetime.now()


class SessionManager:
	"""会话管理器

	管理所有活跃的会话，提供会话创建、获取、删除等功能。
	"""

	def __init__(self) -> None:
		"""初始化会话管理器"""
		self.sessions: dict[str, McpSession] = {}

	def create_session(self) -> McpSession:
		"""创建新会话

		Returns:
			新创建的会话对象
		"""
		session_id = str(uuid.uuid4())
		session = McpSession(session_id)
		self.sessions[session_id] = session
		return session

	def get_session(self, session_id: str) -> McpSession | None:
		"""获取会话

		Args:
			session_id: 会话 ID

		Returns:
			会话对象，如果不存在或已过期返回 None
		"""
		session = self.sessions.get(session_id)
		if session and not session.is_expired():
			session.update_activity()
			return session

		# 清理过期会话
		if session and session.is_expired():
			self.delete_session(session_id)

		return None

	def get_or_create_default_session(self) -> McpSession:
		"""获取或创建默认会话

		用于没有会话 ID 的客户端（如 MCP Inspector）

		Returns:
			默认会话对象
		"""
		default_session_id = 'default-session'
		session = self.get_session(default_session_id)
		if session:
			return session

		# 创建默认会话
		session = McpSession(default_session_id)
		self.sessions[default_session_id] = session
		return session

	def delete_session(self, session_id: str) -> bool:
		"""删除会话

		Args:
			session_id: 会话 ID

		Returns:
			True 表示删除成功，False 表示会话不存在
		"""
		if session_id in self.sessions:
			del self.sessions[session_id]
			return True
		return False

	def cleanup_expired(self) -> None:
		"""清理所有过期会话"""
		expired = [
			sid for sid, session in self.sessions.items() if session.is_expired()
		]
		for sid in expired:
			self.delete_session(sid)


# JSON-RPC 消息类型定义
class JsonRpcRequest(BaseModel):
	"""JSON-RPC 2.0 请求"""

	jsonrpc: str = Field(default='2.0', description='JSON-RPC 版本')
	id: str | int | None = Field(
		default=None, description='请求 ID（通知消息可以没有ID）'
	)
	method: str = Field(description='方法名')
	params: dict[str, Any] | None = Field(default=None, description='参数')


class JsonRpcResponse(BaseModel):
	"""JSON-RPC 2.0 响应"""

	jsonrpc: str = Field(default='2.0', description='JSON-RPC 版本')
	id: str | int | None = Field(description='请求 ID')
	result: Any | None = Field(default=None, description='结果')
	error: dict[str, Any] | None = Field(default=None, description='错误信息')


class JsonRpcError:
	"""JSON-RPC 错误码"""

	PARSE_ERROR = -32700
	INVALID_REQUEST = -32600
	METHOD_NOT_FOUND = -32601
	INVALID_PARAMS = -32602
	INTERNAL_ERROR = -32603


class McpTransportHandler:
	"""MCP 传输层处理器

	实现符合 MCP 2025-06-18 标准的 Streamable HTTP 传输。
	支持 POST、GET、DELETE 方法。
	"""

	def __init__(
		self,
		tools: list[BaseMcpTool],
		resources: ResourceManager,
		allowed_origins: list[str] | None = None,
		tool_filter: ToolFilter | None = None,
		data_masker: SensitiveDataMasker | None = None,
		access_logger: AccessLogger | None = None,
	) -> None:
		"""初始化传输处理器

		Args:
			tools: MCP Tools 列表
			resources: Resource 管理器
			allowed_origins: 允许的 CORS 来源列表
			tool_filter: 工具过滤器（可选）
			data_masker: 敏感信息脱敏器（可选）
			access_logger: 访问日志记录器（可选）
		"""
		self.tools = tools
		self.resources = resources
		self.allowed_origins = allowed_origins or [
			'http://localhost',
			'http://127.0.0.1',
		]
		self.session_manager = SessionManager()
		self.tool_filter = tool_filter
		self.data_masker = data_masker
		self.access_logger = access_logger

	def _verify_protocol_version(self, version: str | None) -> None:
		"""验证 MCP 协议版本

		Args:
			version: 协议版本字符串

		Raises:
			HTTPException: 当版本不匹配时抛出 400 错误
		"""
		# 临时禁用协议版本验证以兼容 MCP Inspector
		# MCP Inspector 可能不发送 Mcp-Protocol-Version 头
		if version and version != MCP_PROTOCOL_VERSION:
			# 只有当提供了版本但不匹配时才报错
			raise HTTPException(
				status_code=400,
				detail=f'Unsupported protocol version. Required: {MCP_PROTOCOL_VERSION}, got: {version}',
			)

	def _verify_origin(self, origin: str | None) -> None:
		"""验证 Origin 头（防止 DNS rebinding 攻击）

		Args:
			origin: Origin 头值

		Raises:
			HTTPException: 当 Origin 不在允许列表时抛出 403 错误
		"""
		if not origin:
			return

		# 检查是否在允许列表中
		if '*' not in self.allowed_origins:
			origin_allowed = any(
				origin.startswith(allowed) for allowed in self.allowed_origins
			)
			if not origin_allowed:
				raise HTTPException(
					status_code=403,
					detail=f'Origin not allowed: {origin}',
				)

	async def _handle_initialize(
		self, session: McpSession, params: dict[str, Any] | None
	) -> dict[str, Any]:
		"""处理 initialize 方法

		Args:
			session: 当前会话
			params: 初始化参数

		Returns:
			初始化响应
		"""
		# 标记会话为已初始化
		session.initialized = True

		# 保存客户端能力
		if params:
			session.capabilities = params.get('capabilities', {})

		# 返回服务器能力
		return {
			'protocolVersion': MCP_PROTOCOL_VERSION,
			'capabilities': {
				'tools': {'supported': True},
				'resources': {'supported': True},
				'streaming': {'supported': True},
			},
			'serverInfo': {
				'name': 'openapi-mcp-server',
				'version': '0.1.0',
			},
		}

	async def _handle_tools_list(self) -> dict[str, Any]:
		"""处理 tools/list 方法

		Returns:
			工具列表响应
		"""
		tools_list = []
		for tool in self.tools:
			tool_info: dict[str, Any] = {
				'name': tool.name,
				'description': tool.description,
			}
			# MCP 规范要求所有工具都必须有 inputSchema
			tool_info['inputSchema'] = tool.input_schema or {
				'type': 'object',
				'properties': {},
				'required': [],
			}
			tools_list.append(tool_info)

		return {'tools': tools_list}

	async def _handle_tools_call(self, params: dict[str, Any] | None) -> dict[str, Any]:
		"""处理 tools/call 方法

		Args:
			params: 调用参数，包含 name 和 arguments

		Returns:
			工具执行结果

		Raises:
			ValueError: 当参数无效或工具不存在时
		"""
		if not params or 'name' not in params:
			raise ValueError('Missing required parameter: name')

		tool_name = params['name']
		tool_args = params.get('arguments', {})

		# 应用工具过滤器
		if self.tool_filter:
			if not self.tool_filter.should_allow(tool_name, **tool_args):
				# 记录访问拒绝
				if self.access_logger:
					self.access_logger.log_access_denied(
						tool_name,
						tool_args,
						reason='Blocked by tool filter',
					)
				raise ValueError(f'Access denied: Tool {tool_name} is not allowed')

		# 查找工具
		tool = None
		for t in self.tools:
			if t.name == tool_name:
				tool = t
				break

		if not tool:
			raise ValueError(f'Tool not found: {tool_name}')

		# 执行工具并记录日志
		try:
			result = await tool.execute(**tool_args)

			# 记录成功调用
			if self.access_logger:
				self.access_logger.log_tool_call(tool_name, tool_args, result='success')

		except Exception as e:
			# 记录失败调用
			if self.access_logger:
				self.access_logger.log_tool_call(tool_name, tool_args, error=str(e))
			raise

		# 转换为 MCP 响应格式
		from mcp.types import TextContent

		content_list = []
		for content in result.content:
			if isinstance(content, TextContent):
				# 应用敏感信息脱敏
				text = content.text
				if self.data_masker:
					text = self.data_masker.mask_text(text)

				content_list.append(
					{
						'type': content.type,
						'text': text,
					}
				)

		return {
			'content': content_list,
			'isError': result.isError or False,
		}

	async def _handle_resources_list(self) -> dict[str, Any]:
		"""处理 resources/list 方法

		Returns:
			资源列表响应
		"""
		resources_list = self.resources.list_resources()

		return {
			'resources': [
				{
					'uri': str(resource.uri),
					'name': resource.name,
					'description': resource.description,
					'mimeType': resource.mimeType,
				}
				for resource in resources_list
			]
		}

	async def _handle_resources_read(
		self, params: dict[str, Any] | None, session: McpSession | None = None
	) -> dict[str, Any]:
		"""处理 resources/read 方法

		Args:
			params: 读取参数，包含 uri
			session: 当前会话（可选）

		Returns:
			资源内容响应

		Raises:
			ValueError: 当参数无效或资源不存在时
		"""
		if not params or 'uri' not in params:
			raise ValueError('Missing required parameter: uri')

		uri = params['uri']
		start_time = datetime.now()

		# 检查资源访问权限
		if self.access_logger and not self.access_logger.can_access_resource(uri):
			reason = 'Access denied by resource access control'
			logger.warning(f"Resource access denied: {uri} - {reason}")

			if self.access_logger:
				self.access_logger.log_resource_access_denied(
					uri, reason, session_id=session.session_id if session else None
				)

			raise ValueError(f'Access denied to resource: {uri}')

		# 记录资源访问
		logger.info(f"Reading resource: {uri}")
		if self.access_logger:
			self.access_logger.log_resource_access(
				uri, session_id=session.session_id if session else None
			)

		try:
			contents = await self.resources.read_resource(uri)

			# 应用敏感信息脱敏
			if self.data_masker:
				masked_contents = []
				for content in contents:
					if content.type == 'text':
						masked_text = self.data_masker.mask_text(content.text)
						masked_contents.append(
							{
								'type': content.type,
								'text': masked_text,
							}
						)
					else:
						masked_contents.append(
							{
								'type': content.type,
								'data': content.text,  # 对于非文本内容
							}
						)
				result = {'contents': masked_contents}
			else:
				result = {
					'contents': [
						{
							'type': content.type,
							'text': content.text,
						}
						for content in contents
					]
				}

			# 记录性能指标
			duration = (datetime.now() - start_time).total_seconds()
			logger.info(f"Resource read completed: {uri} in {duration:.3f}s")

			# 记录成功访问
			if self.access_logger:
				self.access_logger.log_resource_access(
					uri,
					session_id=session.session_id if session else None,
					duration=duration
				)

			return result

		except Exception as e:
			# 记录失败访问
			duration = (datetime.now() - start_time).total_seconds()
			logger.error(f"Resource read failed: {uri} in {duration:.3f}s - {e}")

			if self.access_logger:
				self.access_logger.log_resource_access(
					uri,
					session_id=session.session_id if session else None,
					duration=duration,
					error=str(e)
				)

			# 重新抛出更具体的错误
			if "not found" in str(e).lower():
				raise ValueError(f'Resource not found: {uri}') from e
			elif "permission" in str(e).lower():
				raise ValueError(f'Access denied to resource: {uri}') from e
			else:
				raise RuntimeError(f'Failed to read resource {uri}: {e}') from e

	async def _process_jsonrpc_request(
		self, request: JsonRpcRequest, session: McpSession
	) -> JsonRpcResponse:
		"""处理 JSON-RPC 请求

		Args:
			request: JSON-RPC 请求对象
			session: 当前会话

		Returns:
			JSON-RPC 响应对象
		"""
		try:
			# 处理通知消息（没有 id 的消息）
			if request.id is None:
				# 处理 notifications/initialized
				if request.method == 'notifications/initialized':
					session.initialized = True
					# 通知消息不需要响应
					return None
				# 其他通知消息也可以在这里处理
				return None

			# 检查会话是否已初始化（initialize 方法除外）
			if request.method != 'initialize' and not session.initialized:
				return JsonRpcResponse(
					id=request.id,
					error={
						'code': JsonRpcError.INVALID_REQUEST,
						'message': 'Session not initialized',
					},
				)

			# 路由到对应的处理方法
			if request.method == 'initialize':
				result = await self._handle_initialize(session, request.params)
			elif request.method == 'tools/list':
				result = await self._handle_tools_list()
			elif request.method == 'tools/call':
				result = await self._handle_tools_call(request.params)
			elif request.method == 'resources/list':
				result = await self._handle_resources_list()
			elif request.method == 'resources/read':
				result = await self._handle_resources_read(request.params, session)
			else:
				return JsonRpcResponse(
					id=request.id,
					error={
						'code': JsonRpcError.METHOD_NOT_FOUND,
						'message': f'Method not found: {request.method}',
					},
				)

			return JsonRpcResponse(id=request.id, result=result)

		except ValueError as e:
			return JsonRpcResponse(
				id=request.id,
				error={
					'code': JsonRpcError.INVALID_PARAMS,
					'message': str(e),
				},
			)

		except Exception as e:
			return JsonRpcResponse(
				id=request.id,
				error={
					'code': JsonRpcError.INTERNAL_ERROR,
					'message': f'Internal error: {e}',
				},
			)

	async def handle_post(
		self,
		request: Request,
		mcp_protocol_version: str | None = None,
		mcp_session_id: str | None = None,
		origin: str | None = None,
		accept: str | None = None,
	) -> Response:
		"""处理 POST 请求

		接收 JSON-RPC 消息，可返回 JSON 响应或 SSE 流。

		Args:
			request: FastAPI 请求对象
			mcp_protocol_version: MCP 协议版本头
			mcp_session_id: 会话 ID 头
			origin: Origin 头
			accept: Accept 头

		Returns:
			JSON 响应或 SSE 流响应

		Raises:
			HTTPException: 当请求无效时
		"""
		# 验证协议版本
		self._verify_protocol_version(mcp_protocol_version)

		# 验证 Origin
		self._verify_origin(origin)

		# 获取或创建会话
		if mcp_session_id:
			session = self.session_manager.get_session(mcp_session_id)
			if not session:
				raise HTTPException(
					status_code=404, detail='Session not found or expired'
				)
		else:
			# 为没有会话 ID 的客户端（如 MCP Inspector）使用默认会话
			session = self.session_manager.get_or_create_default_session()

		# 解析 JSON-RPC 消息
		try:
			body = await request.json()
			jsonrpc_request = JsonRpcRequest(**body)
		except Exception as e:
			raise HTTPException(
				status_code=400,
				detail=f'Invalid JSON-RPC request: {e}',
			) from e

		# 处理请求
		jsonrpc_response = await self._process_jsonrpc_request(jsonrpc_request, session)

		# 通知消息不需要响应
		if jsonrpc_response is None:
			return Response(status_code=204)  # No Content

		# 根据 Accept 头决定返回格式
		response_data = jsonrpc_response.model_dump(exclude_none=True)

		if accept == 'text/event-stream':
			# 返回 SSE 流
			async def sse_generator() -> AsyncIterator[str]:
				# 发送响应
				event_data = json.dumps(response_data)
				yield f'data: {event_data}\n\n'

				# 对于 Resources 操作，可以考虑后续推送更新
				if jsonrpc_request.method in ('resources/read', 'resources/list'):
					# TODO: 实现资源变更通知机制
					pass

				# 保持连接，等待后续消息
				# TODO: 实现真正的流式响应

			return StreamingResponse(
				sse_generator(),
				media_type='text/event-stream',
				headers={
					'Mcp-Session-Id': session.session_id,
					'Cache-Control': 'no-cache',
					'Connection': 'keep-alive',
				},
			)
		else:
			# 返回 JSON 响应，添加缓存控制头
			headers = {'Mcp-Session-Id': session.session_id}

			# 为 Resources 响应添加缓存控制
			if jsonrpc_request.method in ('resources/read', 'resources/list'):
				headers['Cache-Control'] = 'max-age=300, private'  # 5分钟缓存
			else:
				headers['Cache-Control'] = 'no-cache'

			return JSONResponse(
				content=response_data,
				headers=headers,
			)

	async def handle_get(
		self,
		mcp_protocol_version: str | None = None,
		mcp_session_id: str | None = None,
		origin: str | None = None,
		accept: str | None = None,
		last_event_id: str | None = None,
	) -> Response:
		"""处理 GET 请求

		打开 SSE 流，允许服务器主动推送消息。

		Args:
			mcp_protocol_version: MCP 协议版本头
			mcp_session_id: 会话 ID 头
			origin: Origin 头
			accept: Accept 头
			last_event_id: 最后接收的事件 ID（用于流恢复）

		Returns:
			SSE 流响应

		Raises:
			HTTPException: 当请求无效时
		"""
		# 验证协议版本
		self._verify_protocol_version(mcp_protocol_version)

		# 验证 Origin
		self._verify_origin(origin)

		# 验证 Accept 头
		if accept != 'text/event-stream':
			raise HTTPException(
				status_code=406,
				detail='Accept header must be text/event-stream',
			)

		# 获取会话
		if not mcp_session_id:
			raise HTTPException(
				status_code=400, detail='Mcp-Session-Id header required'
			)

		session = self.session_manager.get_session(mcp_session_id)
		if not session:
			raise HTTPException(status_code=404, detail='Session not found or expired')

		# 创建 SSE 流
		async def sse_generator() -> AsyncIterator[str]:
			"""生成 SSE 事件流"""
			try:
				# TODO: 如果有 last_event_id，重放错过的消息
				_ = last_event_id  # 避免未使用变量警告

				# 持续发送队列中的消息
				while True:
					try:
						# 等待新消息（带超时）
						message = await asyncio.wait_for(
							session.message_queue.get(),
							timeout=30.0,
						)

						# 发送消息
						event_data = json.dumps(message)
						event_id = str(uuid.uuid4())
						yield f'id: {event_id}\n'
						yield f'data: {event_data}\n\n'

					except TimeoutError:
						# 发送心跳消息
						yield ': heartbeat\n\n'

			except asyncio.CancelledError:
				# 连接被取消
				pass

		return StreamingResponse(
			sse_generator(),
			media_type='text/event-stream',
			headers={
				'Cache-Control': 'no-cache',
				'Connection': 'keep-alive',
			},
		)

	async def handle_delete(
		self,
		mcp_protocol_version: str | None = None,
		mcp_session_id: str | None = None,
		origin: str | None = None,
	) -> Response:
		"""处理 DELETE 请求

		终止会话。

		Args:
			mcp_protocol_version: MCP 协议版本头
			mcp_session_id: 会话 ID 头
			origin: Origin 头

		Returns:
			204 No Content 响应

		Raises:
			HTTPException: 当请求无效时
		"""
		# 验证协议版本
		self._verify_protocol_version(mcp_protocol_version)

		# 验证 Origin
		self._verify_origin(origin)

		# 删除会话
		if not mcp_session_id:
			raise HTTPException(
				status_code=400, detail='Mcp-Session-Id header required'
			)

		success = self.session_manager.delete_session(mcp_session_id)
		if not success:
			raise HTTPException(status_code=404, detail='Session not found')

		return Response(status_code=204)
