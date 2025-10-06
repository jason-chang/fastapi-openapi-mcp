# Claude 模块化记忆系统

这个目录包含了 OpenAPI MCP 项目的模块化记忆配置，为 Claude Code 提供了项目上下文和开发指导。

## 模块结构

每个模块专注于特定的知识领域：

- **[development.md](development.md)** - 开发环境配置、命令和架构认知
- **[project-structure.md](project-structure.md)** - 项目结构、组件关系和架构设计
- **[coding-standards.md](coding-standards.md)** - 编码规范、最佳实践和代码质量
- **[troubleshooting.md](troubleshooting.md)** - 常见问题和故障排除指南
- **[examples.md](examples.md)** - 使用示例和集成模式

## 使用方式

这些模块会被 Claude Code 自动识别和加载，提供：

1. **项目上下文** - 理解项目架构和组件关系
2. **开发指导** - 遵循项目的编码规范和最佳实践
3. **问题解决** - 快速诊断和解决常见问题
4. **示例参考** - 提供各种集成和使用模式

## 维护原则

- **专注性** - 每个模块专注于特定领域
- **实用性** - 包含可执行的具体指导
- **时效性** - 与项目实际状态保持同步
- **可操作性** - 提供具体的命令和代码示例

## 更新指南

当项目发生变化时，相应更新相关模块：

- 新增功能 → 更新 `project-structure.md` 和 `examples.md`
- 编码规范变更 → 更新 `coding-standards.md`
- 发现新问题 → 更新 `troubleshooting.md`
- 开发流程优化 → 更新 `development.md`

这种模块化结构确保了知识组织的清晰性和可维护性，为 Claude Code 提供了高效的项目上下文支持。