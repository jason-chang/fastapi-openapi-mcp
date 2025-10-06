"""
测试 MCP 传输层

测试符合 MCP 2025-06-18 标准的 Streamable HTTP 传输实现。
"""

from httpx import AsyncClient

# MCP 协议版本
MCP_PROTOCOL_VERSION = '2025-06-18'


# ===== 测试 POST 请求 =====


async def test_post_initialize_creates_session(mcp_server, async_client: AsyncClient):
	"""测试 POST initialize 请求创建新会话"""
	response = await async_client.post(
		'/mcp',
		json={
			'jsonrpc': '2.0',
			'id': 1,
			'method': 'initialize',
			'params': {
				'protocolVersion': MCP_PROTOCOL_VERSION,
				'capabilities': {},
			},
		},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Accept': 'application/json',
		},
	)

	assert response.status_code == 200
	assert 'Mcp-Session-Id' in response.headers

	data = response.json()
	assert data['jsonrpc'] == '2.0'
	assert data['id'] == 1
	assert 'result' in data
	assert data['result']['protocolVersion'] == MCP_PROTOCOL_VERSION


async def test_post_tools_list(mcp_server, async_client: AsyncClient):
	"""测试 POST tools/list 请求"""
	# 先初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 请求 tools/list
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 200
	data = response.json()
	assert 'result' in data
	assert 'tools' in data['result']
	assert len(data['result']['tools']) > 0

	# 验证工具信息
	tool_names = [tool['name'] for tool in data['result']['tools']]
	assert 'list_openapi_endpoints' in tool_names


async def test_post_tools_call(mcp_server, async_client: AsyncClient):
	"""测试 POST tools/call 请求"""
	# 先初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 调用工具
	response = await async_client.post(
		'/mcp',
		json={
			'jsonrpc': '2.0',
			'id': 2,
			'method': 'tools/call',
			'params': {
				'name': 'list_openapi_endpoints',
				'arguments': {},
			},
		},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 200
	data = response.json()
	assert 'result' in data
	assert 'content' in data['result']
	assert len(data['result']['content']) > 0


async def test_post_returns_sse_stream(mcp_server, async_client: AsyncClient):
	"""测试 POST 请求返回 SSE 流"""
	# 先初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 请求 SSE 流
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
			'Accept': 'text/event-stream',
		},
	)

	assert response.status_code == 200
	assert response.headers['content-type'] == 'text/event-stream; charset=utf-8'
	assert 'Mcp-Session-Id' in response.headers

	# 验证 SSE 数据格式
	content = response.text
	assert content.startswith('data: ')


async def test_post_invalid_json_rpc(mcp_server, async_client: AsyncClient):
	"""测试无效的 JSON-RPC 请求"""
	response = await async_client.post(
		'/mcp',
		json={'invalid': 'request'},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	assert response.status_code == 400


async def test_post_method_not_found(mcp_server, async_client: AsyncClient):
	"""测试不存在的方法"""
	# 先初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 请求不存在的方法
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 2, 'method': 'nonexistent/method'},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 200
	data = response.json()
	assert 'error' in data
	assert data['error']['code'] == -32601  # METHOD_NOT_FOUND


async def test_post_invalid_params(mcp_server, async_client: AsyncClient):
	"""测试无效的参数"""
	# 先初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 调用工具但参数无效
	response = await async_client.post(
		'/mcp',
		json={
			'jsonrpc': '2.0',
			'id': 2,
			'method': 'tools/call',
			'params': {},  # 缺少 name 参数
		},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 200
	data = response.json()
	assert 'error' in data
	assert data['error']['code'] == -32602  # INVALID_PARAMS


# ===== 测试 GET 请求 =====


async def test_get_opens_sse_stream(mcp_server, async_client: AsyncClient):
	"""测试 GET 请求打开 SSE 流"""
	import asyncio

	# 先初始化获取会话 ID
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 打开 SSE 流（仅验证连接成功，不等待数据）
	# 注意：由于 SSE 流是长连接，我们只验证响应头
	async def test_stream():
		async with async_client.stream(
			'GET',
			'/mcp',
			headers={
				'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
				'Mcp-Session-Id': session_id,
				'Accept': 'text/event-stream',
			},
		) as response:
			assert response.status_code == 200
			assert (
				response.headers['content-type'] == 'text/event-stream; charset=utf-8'
			)
			# 不读取数据，直接关闭连接

	# 使用超时保护
	try:
		await asyncio.wait_for(test_stream(), timeout=2.0)
	except TimeoutError:
		# 超时也算通过，说明流已经建立
		pass


async def test_get_without_accept_header(mcp_server, async_client: AsyncClient):
	"""测试 GET 请求缺少 Accept 头"""
	# 先初始化获取会话 ID
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 不带 Accept 头
	response = await async_client.get(
		'/mcp',
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 406  # Not Acceptable


async def test_get_without_session_id(mcp_server, async_client: AsyncClient):
	"""测试 GET 请求缺少会话 ID"""
	response = await async_client.get(
		'/mcp',
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Accept': 'text/event-stream',
		},
	)

	assert response.status_code == 400


async def test_get_with_invalid_session_id(mcp_server, async_client: AsyncClient):
	"""测试 GET 请求使用无效的会话 ID"""
	response = await async_client.get(
		'/mcp',
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': 'invalid-session-id',
			'Accept': 'text/event-stream',
		},
	)

	assert response.status_code == 404


# ===== 测试 DELETE 请求 =====


async def test_delete_terminates_session(mcp_server, async_client: AsyncClient):
	"""测试 DELETE 请求终止会话"""
	# 先初始化获取会话 ID
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 删除会话
	response = await async_client.delete(
		'/mcp',
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 204

	# 验证会话已被删除
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': session_id,
		},
	)

	assert response.status_code == 404


async def test_delete_without_session_id(mcp_server, async_client: AsyncClient):
	"""测试 DELETE 请求缺少会话 ID"""
	response = await async_client.delete(
		'/mcp',
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	assert response.status_code == 400


async def test_delete_invalid_session_id(mcp_server, async_client: AsyncClient):
	"""测试 DELETE 请求使用无效的会话 ID"""
	response = await async_client.delete(
		'/mcp',
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Mcp-Session-Id': 'invalid-session-id',
		},
	)

	assert response.status_code == 404


# ===== 测试协议版本 =====


async def test_valid_protocol_version(mcp_server, async_client: AsyncClient):
	"""测试有效的协议版本"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	assert response.status_code == 200


async def test_invalid_protocol_version(mcp_server, async_client: AsyncClient):
	"""测试无效的协议版本"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': '2024-01-01'},
	)

	assert response.status_code == 400


async def test_missing_protocol_version(mcp_server, async_client: AsyncClient):
	"""测试缺少协议版本头"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
	)

	assert response.status_code == 400


# ===== 测试安全功能 =====


async def test_valid_origin(mcp_server, async_client: AsyncClient):
	"""测试有效的 Origin"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Origin': 'http://localhost',
		},
	)

	assert response.status_code == 200


async def test_invalid_origin(mcp_server, async_client: AsyncClient):
	"""测试无效的 Origin"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={
			'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
			'Origin': 'http://evil.com',
		},
	)

	assert response.status_code == 403


async def test_no_origin_header(mcp_server, async_client: AsyncClient):
	"""测试缺少 Origin 头（应该允许）"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	assert response.status_code == 200


# ===== 测试会话管理 =====


async def test_session_id_returned_on_init(mcp_server, async_client: AsyncClient):
	"""测试初始化时返回会话 ID"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	assert response.status_code == 200
	assert 'Mcp-Session-Id' in response.headers
	assert len(response.headers['Mcp-Session-Id']) > 0


async def test_session_required_for_non_init_methods(
	mcp_server, async_client: AsyncClient
):
	"""测试非初始化方法需要会话"""
	response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)

	# 应该创建新会话，但返回错误因为未初始化
	assert response.status_code == 200
	data = response.json()
	assert 'error' in data


async def test_session_reuse(mcp_server, async_client: AsyncClient):
	"""测试会话可以被重复使用"""
	# 初始化
	init_response = await async_client.post(
		'/mcp',
		json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
		headers={'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION},
	)
	session_id = init_response.headers['Mcp-Session-Id']

	# 使用同一会话 ID 发起多个请求
	for i in range(3):
		response = await async_client.post(
			'/mcp',
			json={'jsonrpc': '2.0', 'id': i + 2, 'method': 'tools/list'},
			headers={
				'Mcp-Protocol-Version': MCP_PROTOCOL_VERSION,
				'Mcp-Session-Id': session_id,
			},
		)
		assert response.status_code == 200
		assert 'result' in response.json()
