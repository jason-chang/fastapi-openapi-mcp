# 开发任务清单 (TODO)

> 📅 创建时间: 2025-10-05 (重新设计)
>
> 🎯 目标: 实现基于 MCP 2025-06-18 标准的 FastAPI OpenAPI MCP Server
>
> 📦 架构: **Resources + Tools 混合模式**，提供直观的资源访问和强大的查询能力

---

## 📊 总体进度

- [x] 阶段一: 核心架构重构 (2/2)
- [x] 阶段二: 实现 Resources (5/5)
- [x] 阶段三: 实现 Tools (3/3)
- [x] 阶段四: 集成和优化 (5/5)
- [ ] 阶段五: 质量保证和发布 (0/7)

**总计**: 26/31 任务完成

---

## 🏗️ 阶段一: 核心架构重构

### ✅ Step 1: MCP Server 架构升级

#### ✅ Step 1.1: 升级到 Resources+Tools 混合架构
- [x] 分析现有 9 个 Tools 的功能重构需求
- [x] 设计 Resources URI 方案:
  - `openapi://spec` - 完整 OpenAPI spec
  - `openapi://endpoints` - 端点列表
  - `openapi://endpoints/{path}` - 具体端点
  - `openapi://models` - 模型列表
  - `openapi://models/{name}` - 具体模型
  - `openapi://tags` - 标签列表
  - `openapi://tags/{tag}/endpoints` - 按标签分组的端点
- [x] 重构 `OpenApiMcpServer` 类
  - [x] 添加 Resources 能力声明
  - [x] 实现 Resources 基础接口
  - [ ] 重构现有 Tools 为新的 4 个核心 Tools
- [x] 更新传输层支持 Resources 操作

**验收标准**:
- MCP Server 声明 resources 和 tools 能力
- 支持 resources/list 和 resources/read 操作
- 现有 9 个 Tools 重构为 4 个新的核心 Tools

#### ✅ Step 1.2: 实现 Resources 基础设施
- [x] 创建 `openapi_mcp/resources/` 目录
- [x] 实现 `BaseResource` 抽象基类
  - [x] 定义 URI 解析接口
  - [x] 实现缓存机制
  - [ ] 添加权限检查
- [x] 实现 `ResourceManager` 类
  - [x] 资源注册和管理
  - [x] URI 路由解析
  - [x] 响应格式化
- [x] 添加 Resource 相关类型定义

**验收标准**:
- Resource 基类可以被正常继承
- ResourceManager 能正确路由 URI 请求
- 支持细粒度缓存和权限控制

---

## 🌐 阶段二: Resources 实现

### ✅ Step 2: 核心 Resources ✅

#### ✅ Step 2.1: 实现 OpenAPI Spec Resource
- [x] 创建 `openapi_mcp/resources/spec.py`
- [x] 实现 `OpenApiSpecResource` 类
  - [x] URI: `openapi://spec`
  - [x] 返回完整 OpenAPI 规范
  - [x] 支持按需返回部分规范（可选）
- [x] 实现缓存机制
- [x] 编写单元测试

**验收标准**:
- ✅ 能返回完整的 OpenAPI spec
- ✅ 支持 JSON 和 YAML 格式
- ✅ 缓存机制正常工作

#### ✅ Step 2.2: 实现 Endpoints Resources
- [x] 创建 `openapi_mcp/resources/endpoints.py`
- [x] 实现 `EndpointsListResource` 类
  - [x] URI: `openapi://endpoints`
  - [x] 返回所有端点的概要信息
- [x] 实现 `EndpointResource` 类
  - [x] URI: `openapi://endpoints/{path}`
  - [x] 支持多方法端点
  - [x] 返回端点详细信息
- [x] 实现 URI 路径参数解析
- [x] 编写单元测试

**验收标准**:
- ✅ 能列出所有端点概要
- ✅ 能获取具体端点详情
- ✅ 正确处理路径参数（如 `/users/{id}`）

#### ✅ Step 2.3: 实现 Models Resources
- [x] 创建 `openapi_mcp/resources/models.py`
- [x] 实现 `ModelsListResource` 类
  - [x] URI: `openapi://models`
  - [x] 返回所有模型概要
- [x] 实现 `ModelResource` 类
  - [x] URI: `openapi://models/{name}`
  - [x] 解析 `$ref` 引用
  - [x] 返回完整模型定义
- [x] 实现嵌套引用解析
- [x] 编写单元测试

**验收标准**:
- ✅ 能列出所有模型概要
- ✅ 能获取具体模型完整定义
- ✅ 正确解析嵌套的 `$ref` 引用

#### ✅ Step 2.4: 实现 Tags Resources
- [x] 创建 `openapi_mcp/resources/tags.py`
- [x] 实现 `TagsListResource` 类
  - [x] URI: `openapi://tags`
  - [x] 返回所有标签及描述
- [x] 实现 `TagEndpointsResource` 类
  - [x] URI: `openapi://tags/{tag}/endpoints`
  - [x] 返回该标签下的所有端点
- [x] 实现标签统计功能
- [x] 编写单元测试

**验收标准**:
- ✅ 能列出所有标签及统计信息
- ✅ 能按标签获取相关端点
- ✅ 支持不存在的标签处理

#### ✅ Step 2.5: 编写 Resources 集成测试
- [x] 创建 `tests/resources/test_integration.py`
- [x] 测试完整的 Resources 工作流
  - [x] 资源发现和列表
  - [x] 资源读取和解析
  - [x] 错误处理和边界情况
  - [x] 性能和缓存效果
- [x] 测试与 Tools 的协同工作
- [x] 验证 MCP 规范合规性

**验收标准**:
- ✅ 所有 Resources 操作正常工作
- ✅ 错误处理完善
- ✅ 与现有 Tools 无冲突
- ✅ 14个集成测试全部通过

---

## 🔧 阶段三: 实现 Tools ✅

### ✅ Step 3: 实现 2 个核心 Tools ✅

#### ✅ Step 3.1: 实现 search_endpoints Tool ✅
- [x] 创建 `openapi_mcp/tools/search.py`
- [x] 实现 `SearchEndpointsTool` 类
  - [x] 复杂搜索和过滤功能
  - [x] 支持按路径、方法、标签、描述等多维度搜索
  - [x] 支持正则表达式和模糊匹配
- [x] 内部使用 Resources 优化性能
- [x] 编写单元测试

**验收标准**:
- [x] 支持复杂的搜索语法
- [x] 搜索性能优秀
- [x] 测试覆盖率 > 85%

#### ✅ Step 3.2: 实现 generate_examples Tool ✅
- [x] 实现 `GenerateExampleTool` 类
  - [x] 根据模型定义生成调用示例
  - [x] 支持多种示例格式（JSON、cURL、Python等）
  - [x] 处理引用和嵌套结构
  - [x] 支持自定义示例策略
- [x] 整合现有示例生成功能
- [x] 编写单元测试

**验收标准**:
- [x] 生成的示例符合规范
- [x] 支持复杂模型和引用
- [x] 示例格式多样
- [x] 整合旧 Tools 的示例功能

#### ✅ Step 3.6: 编写 Tools 集成测试 ✅
- [x] 创建 `tests/tools/test_core.py`
- [x] 测试所有新的核心 Tools
- [x] 添加 Tools 与 Resources 协同测试
- [x] 性能基准测试
- [x] 复杂场景测试

**验收标准**:
- [x] 所有新 Tools 正常工作
- [x] 与 Resources 协同良好
- [x] 性能指标达标
- [x] 测试覆盖率 > 90%

---

## 🔗 阶段四: 集成和优化

### ✅ Step 4: 传输层和集成优化

#### ✅ Step 4.1: 优化传输层
- [x] 更新 `transport.py` 支持 Resources
- [x] 实现 Resources 的 SSE 推送
- [x] 优化 JSON-RPC 消息处理
- [x] 增强错误处理和日志
- [x] 编写传输层测试

**验收标准**:
- ✅ Resources 数据返回正常
- ✅ SSE 推送稳定可靠
- ✅ 错误处理完善

#### ✅ Step 4.2: 安全功能集成
- [x] 扩展安全功能支持 Resources
  - [x] Resource 访问权限控制
  - [x] 敏感信息脱敏
  - [x] 访问日志记录
- [x] 实现细粒度权限控制
- [x] 更新安全测试

**验收标准**:
- ✅ Resources 安全控制到位
- ✅ 敏感信息正确脱敏
- ✅ 访问日志完整

#### ✅ Step 4.3: 性能优化
- [x] 实现多级缓存策略
- [x] 优化大 OpenAPI spec 处理
- [x] 实现并发处理优化
- [x] 添加性能监控
- [x] 性能基准测试

**验收标准**:
- ✅ 响应时间 < 100ms (缓存命中)
- ✅ 支持大型 API (> 1000 端点)
- ✅ 内存使用 < 100MB

#### ✅ Step 4.4: 配置系统增强
- [x] 扩展配置支持 Resources 设置
- [x] 实现动态配置更新
- [x] 添加配置验证
- [x] 配置文档和示例

**验收标准**:
- 配置系统灵活完整
- 支持运行时配置更新
- 配置验证完善

#### Step 4.5: 集成测试升级
- [ ] 创建全面的集成测试套件
- [ ] 测试 Resources + Tools 协同工作
- [ ] 端到端场景测试
- [ ] 压力和稳定性测试
- [ ] 测试覆盖率 > 80%

**验收标准**:
- 所有组件协同工作正常
- 端到端场景测试通过
- 系统稳定性良好
- 测试覆盖率 > 80%

---

## 📋 阶段五: 质量保证和发布

### ✅ Step 5: 文档和发布准备

#### Step 5.1: 使用示例更新
- [ ] 更新 `examples/` 目录
  - [ ] Resources 使用示例
  - [ ] Tools 使用示例
  - [ ] 混合模式使用示例
  - [ ] 高级功能示例
- [ ] 创建 `examples/resources_vs_tools.py` 对比示例
- [ ] 添加性能测试示例

**验收标准**:
- 示例覆盖所有主要功能
- 代码可运行且文档清晰
- 包含最佳实践指导

#### Step 5.2: 文档完善
- [ ] 更新 `README.md`
  - [ ] Resources + Tools 架构说明
  - [ ] 快速开始指南
  - [ ] 性能特性说明
  - [ ] 迁移指南（如果需要）
- [ ] 创建 `docs/RESOURCES.md`
  - [ ] Resources 设计理念
  - [ ] URI 结构说明
  - [ ] 使用场景和最佳实践
- [ ] 更新 `docs/API.md`
  - [ ] 所有 Resources API 文档
  - [ ] 所有 Tools API 文档
  - [ ] 示例和用法

**验收标准**:
- 文档完整准确
- 包含充足示例
- 易于理解和使用

#### Step 5.3: 测试覆盖率检查
- [ ] 运行完整测试套件
- [ ] 确保测试覆盖率 > 85%
- [ ] 补充缺失的测试用例
- [ ] 生成覆盖率报告
- [ ] 性能基准测试

**验收标准**:
- 测试覆盖率 > 85%
- 所有核心功能有测试
- 性能指标达标

#### Step 5.4: 代码质量检查
- [ ] 运行 `basedpyright` 类型检查
- [ ] 运行 `ruff format` 代码格式化
- [ ] 运行 `ruff check --fix` 代码检查
- [ ] 代码审查和重构
- [ ] 安全扫描

**验收标准**:
- 类型检查 100% 通过
- 代码风格一致
- 无安全漏洞

#### Step 5.5: CI/CD 配置
- [ ] 创建 `.github/workflows/ci.yml`
  - [ ] 代码质量检查
  - [ ] 测试运行
  - [ ] 覆盖率报告
  - [ ] 性能测试
- [ ] 创建 `.github/workflows/release.yml`
  - [ ] 自动发布到 PyPI
  - [ ] GitHub Release 创建
  - [ ] 文档部署

**验收标准**:
- CI 流程稳定可靠
- 发布流程自动化
- 质量门禁有效

#### Step 5.6: 版本发布准备
- [ ] 更新 `CHANGELOG.md`
  - [ ] 记录所有新功能
  - [ ] 记录重大变更
  - [ ] 记录 bug 修复
- [ ] 更新版本号到 `v1.0.0`
- [ ] 准备发布说明
- [ ] 创建发布标签

**验收标准**:
- 变更日志完整
- 版本号符合语义化版本
- 发布说明清晰

#### Step 5.7: 最终发布
- [ ] 最终测试验证
- [ ] 创建 Git tag
- [ ] 推送到 GitHub
- [ ] 触发发布流程
- [ ] 验证 PyPI 包
- [ ] 发布公告

**验收标准**:
- 所有测试通过
- 包成功发布到 PyPI
- 文档部署成功

---

## 🎯 架构设计决策

### Resources vs Tools 使用场景

**使用 Resources 当:**
- 需要直接访问特定的 API 文档数据
- 想要浏览式的探索 API 结构
- 需要缓存特定资源
- 客户端支持资源发现

**使用 Tools 当:**
- 需要复杂的查询和搜索逻辑
- 需要数据对比和分析
- 需要批量操作
- 需要自定义输出格式

**混合模式优势:**
- Resources 提供直观的数据访问
- Tools 提供强大的处理能力
- 两者互补，提供最佳用户体验
- 简化的架构，更好的性能

---

## 📝 开发建议

### 每个会话的工作流程

1. 📖 **开始前**: 查看 TODO.md，选择具体 Step
2. 💻 **开发**: 按照验收标准实现功能
3. ✅ **测试**: 编写并运行测试确保通过
4. 📋 **更新**: 更新 TODO.md 进度
5. 💾 **提交**: 创建有意义的 Git commit

### 质量检查清单

每个 Step 完成前运行:

```bash
# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check . --fix

# 类型检查
uv run basedpyright

# 运行测试
uv run pytest

# 查看覆盖率
uv run pytest --cov=openapi_mcp --cov-report=term-missing
```

### 建议的会话分割

- **会话 1**: Step 1 (架构重构)
- **会话 2-3**: Step 2 (Resources 实现)
- **会话 4**: Step 3 (核心 Tools 优化)
- **会话 5**: Step 4 (集成优化)
- **会话 6**: Step 5 (文档和发布)

---

**最后更新**: 2025-10-05
**架构**: Resources + Tools 混合模式
**目标**: 打造 MCP 生态中最好的 OpenAPI 集成方案