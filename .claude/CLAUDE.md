# Claude Code 项目指导

> 🚀 **模块化记忆系统**：本项目的 Claude Code 配置采用模块化结构，提供分模块的记忆/配置支持。

## 📁 模块化配置

项目指导信息已拆分为专门的模块，位于 `.claude/memory/` 目录：

### 🔧 [开发环境配置](./memory/development.md)
- 环境设置和依赖管理
- 开发命令（测试、代码质量、MCP Inspector）
- 项目架构认知和核心组件
- 集成模式和安全功能

### 🏗️ [项目结构和架构](./memory/project-structure.md)
- 完整的目录结构
- 核心类关系图
- 传输层架构
- 安全架构和缓存策略
- 扩展机制和依赖关系

### 📝 [编码规范](./memory/coding-standards.md)
- Python 版本要求（3.13+）
- 代码风格和命名约定
- 文档字符串规范
- 类型注解和异步编程规范
- 错误处理和性能优化
- 安全编码实践

### 🔍 [故障排除](./memory/troubleshooting.md)
- 常见启动问题
- MCP Inspector 问题
- HTTP 模式问题
- 测试和性能问题
- 调试技巧和帮助指南

## 🎯 快速参考

### 立即开始开发
```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest

# MCP Inspector 测试（stdio 模式）
npx @modelcontextprotocol/inspector uv run python examples/mcp_inspector_test.py

# MCP Inspector 测试（HTTP 模式）
npx @modelcontextprotocol/inspector uv run python examples/mcp_http_example.py
```

### 核心架构认知
- **OpenApiMcpServer**: 主要服务器类，管理工具和缓存
- **9个内置工具**: 端点管理、模型操作、搜索功能
- **三层安全机制**: 工具过滤、数据脱敏、访问日志
- **多协议支持**: JSON-RPC、SSE、会话管理

### 代码质量标准
- Python 3.13+ with 类型注解
- 全程 async/await 模式
- ruff 格式化 + basedpyright 类型检查
- 测试覆盖率 >80%

## 📋 开发任务

当你在这个项目中工作时，Claude 会：

1. **自动加载相关模块** - 根据当前任务类型加载对应的记忆模块
2. **遵循项目规范** - 严格按照编码规范和最佳实践
3. **理解架构上下文** - 基于项目架构知识做出合理的决策
4. **快速问题诊断** - 利用故障排除指南快速解决问题

## 🔗 相关文件

- [README.md](README.md) - 项目主文档
- [DEVELOPMENT.md](DEVELOPMENT.md) - 开发任务清单
- [pyproject.toml](pyproject.toml) - 项目配置
- [examples/](examples/) - 使用示例

---

这种模块化配置确保了 Claude Code 能够高效理解项目上下文，提供精准的开发指导，同时保持知识的组织性和可维护性。