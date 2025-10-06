#!/usr/bin/env python3
"""
测试可配置格式化器功能
"""

import asyncio

from fastapi import FastAPI

from openapi_mcp import OpenApiMcpConfig, OpenApiMcpServer

# 创建一个简单的 FastAPI 应用用于测试
app = FastAPI(title='Test API', version='1.0.0', description='测试API')


@app.get('/users')
async def list_users():
	"""列出用户"""
	return {'users': []}


@app.post('/users')
async def create_user(user_data: dict):
	"""创建用户"""
	return {'user': user_data}


@app.get('/users/{user_id}')
async def get_user(user_id: int):
	"""获取用户详情"""
	return {'user_id': user_id, 'name': 'Test User'}


async def test_formatter(format_type: str):
	"""测试指定格式的输出"""
	print(f'\n{"=" * 50}')
	print(f'测试 {format_type.upper()} 格式输出:')
	print(f'{"=" * 50}')

	# 创建配置
	config = OpenApiMcpConfig(output_format=format_type, max_output_length=2000)

	# 创建 MCP Server
	mcp_server = OpenApiMcpServer(app, config)

	# 获取第一个工具
	list_tool = mcp_server.tools[0]

	# 执行工具
	result = await list_tool.execute()

	# 输出结果
	if result.content and result.content[0].type == 'text':
		print(result.content[0].text)
	else:
		print('无文本内容')

	if result.isError:
		print(f'错误: {result.content[0].text if result.content else "未知错误"}')


async def main():
	"""主测试函数"""
	# 测试所有格式
	for format_type in ['markdown', 'json', 'plain']:
		await test_formatter(format_type)

	print(f'\n{"=" * 50}')
	print('测试完成!')
	print(f'{"=" * 50}')


if __name__ == '__main__':
	asyncio.run(main())
