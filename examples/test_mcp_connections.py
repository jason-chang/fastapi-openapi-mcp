"""
MCP Server 连接方式测试脚本

提供统一的测试接口，支持 stdin 和 StreamableHTTP 两种连接方式。
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time

import httpx


def test_stdio_connection():
	"""测试 stdio 连接方式"""
	print('🧪 测试 MCP Server stdio 连接...\n')

	# 启动 stdio 服务器进程
	process = subprocess.Popen(
		[sys.executable, 'mcp_stdio_example.py'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
	)

	try:
		# 1. 测试初始化
		print('📝 测试 1: Initialize')
		init_request = {
			'jsonrpc': '2.0',
			'id': 1,
			'method': 'initialize',
			'params': {},
		}

		process.stdin.write(json.dumps(init_request) + '\n')
		process.stdin.flush()

		response = process.stdout.readline()
		result = json.loads(response.strip())

		if 'result' in result:
			print('✅ 初始化成功')
			print(f'   服务器信息: {result["result"]["serverInfo"]}\n')
		else:
			print(f'❌ 初始化失败: {result}')
			return

		# 2. 测试工具列表
		print('📝 测试 2: List Tools')
		tools_request = {
			'jsonrpc': '2.0',
			'id': 2,
			'method': 'tools/list',
			'params': {},
		}

		process.stdin.write(json.dumps(tools_request) + '\n')
		process.stdin.flush()

		response = process.stdout.readline()
		result = json.loads(response.strip())

		if 'result' in result:
			tools = result['result']['tools']
			print(f'✅ 获取工具列表成功，共 {len(tools)} 个工具')
			for tool in tools[:3]:  # 只显示前3个
				print(f'   - {tool["name"]}: {tool["description"]}')
			print('   ...\n')
		else:
			print(f'❌ 获取工具列表失败: {result}')
			return

		# 3. 测试调用工具
		print('📝 测试 3: Call Tool - list_openapi_endpoints')
		call_request = {
			'jsonrpc': '2.0',
			'id': 3,
			'method': 'tools/call',
			'params': {
				'name': 'list_openapi_endpoints',
				'arguments': {},
			},
		}

		process.stdin.write(json.dumps(call_request) + '\n')
		process.stdin.flush()

		response = process.stdout.readline()
		result = json.loads(response.strip())

		if 'result' in result:
			content = result['result']['content'][0]['text']
			print('✅ 调用工具成功')
			print('   接口列表（前200字符）:')
			print(f'   {content[:200]}...\n')
		else:
			print(f'❌ 调用工具失败: {result}')
			return

		print('✅ stdio 连接测试完成！')

	finally:
		# 清理进程
		process.stdin.close()
		process.terminate()
		process.wait()


async def test_http_connection():
	"""测试 HTTP 连接方式"""
	print('🧪 测试 MCP Server HTTP 连接...\n')

	# 启动 HTTP 服务器进程
	process = subprocess.Popen(
		[sys.executable, 'mcp_http_example.py'],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
	)

	# 等待服务器启动
	print('⏳ 等待 HTTP 服务器启动...')
	time.sleep(3)

	try:
		base_url = 'http://localhost:8000'
		mcp_url = f'{base_url}/mcp'

		async with httpx.AsyncClient() as client:
			# 1. 测试初始化
			print('📝 测试 1: Initialize')
			init_request = {
				'jsonrpc': '2.0',
				'id': 1,
				'method': 'initialize',
				'params': {
					'capabilities': {'tools': {}},
				},
			}

			response = await client.post(
				mcp_url,
				json=init_request,
				headers={'Mcp-Protocol-Version': '2025-06-18'},
			)

			if response.status_code == 200:
				result = response.json()
				session_id = response.headers.get('Mcp-Session-Id')
				print(f'✅ 初始化成功，会话 ID: {session_id}')
				print(f'   服务器信息: {result["result"]["serverInfo"]}\n')
			else:
				print(f'❌ 初始化失败: {response.status_code} {response.text}')
				return

			# 2. 测试工具列表
			print('📝 测试 2: List Tools')
			tools_request = {
				'jsonrpc': '2.0',
				'id': 2,
				'method': 'tools/list',
				'params': {},
			}

			response = await client.post(
				mcp_url,
				json=tools_request,
				headers={
					'Mcp-Protocol-Version': '2025-06-18',
					'Mcp-Session-Id': session_id,
				},
			)

			if response.status_code == 200:
				result = response.json()
				tools = result['result']['tools']
				print(f'✅ 获取工具列表成功，共 {len(tools)} 个工具')
				for tool in tools[:3]:  # 只显示前3个
					print(f'   - {tool["name"]}: {tool["description"]}')
				print('   ...\n')
			else:
				print(f'❌ 获取工具列表失败: {response.status_code} {response.text}')
				return

			# 3. 测试调用工具
			print('📝 测试 3: Call Tool - list_openapi_endpoints')
			call_request = {
				'jsonrpc': '2.0',
				'id': 3,
				'method': 'tools/call',
				'params': {
					'name': 'list_openapi_endpoints',
					'arguments': {},
				},
			}

			response = await client.post(
				mcp_url,
				json=call_request,
				headers={
					'Mcp-Protocol-Version': '2025-06-18',
					'Mcp-Session-Id': session_id,
				},
			)

			if response.status_code == 200:
				result = response.json()
				content = result['result']['content'][0]['text']
				print('✅ 调用工具成功')
				print('   接口列表（前200字符）:')
				print(f'   {content[:200]}...\n')
			else:
				print(f'❌ 调用工具失败: {response.status_code} {response.text}')
				return

			# 4. 测试 SSE 流
			print('📝 测试 4: SSE Stream')
			try:
				async with client.stream(
					'GET',
					mcp_url,
					headers={
						'Mcp-Protocol-Version': '2025-06-18',
						'Mcp-Session-Id': session_id,
						'Accept': 'text/event-stream',
					},
					timeout=10.0,
				) as response:
					if response.status_code == 200:
						print('✅ SSE 流连接成功')
						print('   接收前3个事件:')
						count = 0
						async for line in response.aiter_lines():
							if line.startswith('data: '):
								data = json.loads(line[6:])
								print(f'   事件数据: {data}')
								count += 1
								if count >= 3:
									break
					else:
						print(f'❌ SSE 流连接失败: {response.status_code}')
			except Exception as e:
				print(f'❌ SSE 流测试失败: {e}')

			# 5. 清理会话
			print('\n📝 测试 5: Delete Session')
			response = await client.delete(
				mcp_url,
				headers={
					'Mcp-Protocol-Version': '2025-06-18',
					'Mcp-Session-Id': session_id,
				},
			)

			if response.status_code == 204:
				print('✅ 会话删除成功')
			else:
				print(f'❌ 会话删除失败: {response.status_code}')

			print('\n✅ HTTP 连接测试完成！')

	finally:
		# 清理进程
		process.terminate()
		process.wait()


async def main():
	"""主函数"""
	parser = argparse.ArgumentParser(description='测试 MCP Server 连接方式')
	parser.add_argument(
		'--mode',
		choices=['stdio', 'http', 'all'],
		default='all',
		help='选择测试模式: stdio, http 或 all (默认)',
	)

	args = parser.parse_args()

	print('🚀 OpenAPI MCP Server 连接测试')
	print('=' * 50)

	if args.mode in ['stdio', 'all']:
		print('\n📡 测试 stdio 连接方式')
		print('-' * 30)
		test_stdio_connection()

	if args.mode in ['http', 'all']:
		print('\n🌐 测试 HTTP 连接方式')
		print('-' * 30)
		await test_http_connection()

	print('\n🎉 所有测试完成！')


if __name__ == '__main__':
	# 运行主函数
	asyncio.run(main())
