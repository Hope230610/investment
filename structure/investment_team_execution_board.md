# AI 投资决策助手 团队执行任务板

更新时间：2026-03-30

## 1. 文档目的

本任务板用于将产品路线图、MVP 功能优先级、上线准备、研发开工清单和风险边界拆解为团队可执行任务。

本任务板不是“理想状态排期”，而是“带前置条件、阻塞项、阶段交付和基线文档约束的真实推进板”。

## 2. 使用原则

- 所有任务必须归属明确负责人
- 所有任务必须有验收标准
- 所有任务必须有优先级
- 所有任务必须说明是否存在前置依赖
- 所有任务必须说明是否属于上线阻塞项
- 若阻塞项未关闭，不进入下一阶段
- 所有 P0 任务必须绑定对应基线文档
- 若实现与基线文档冲突，优先回到基线文档收口，而不是临时口头决策

## 3. 执行基线文档

以下文档为当前执行阶段必须对齐的基线：

- [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
- [investment_mvp_feature_priority_matrix.md](F:/investment/structure/investment_mvp_feature_priority_matrix.md)
- [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
- [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
- [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
- [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
- [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
- [database_design.md](F:/investment/structure/database_design.md)
- [db_types.ts](F:/investment/structure/db_types.ts)
- [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md)
- [investment_database_check_constraints_draft.md](F:/investment/structure/investment_database_check_constraints_draft.md)
- [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md)
- [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)

## 4. 当前执行前提

以下结论已成立：

- 产品定位已收口为“决策辅助 + 行为干预 + 复盘工具”
- v1 功能范围以三大场景和闭环功能为核心
- 当前项目适合推进“封闭内测”，不适合直接公测
- 当前执行重点是 P0 / P1，不扩范围

以下事实仍需在执行中优先关闭：

- 认证仍带开发态逻辑
- 观察列表仍未完全闭环
- 数据源仍偏 MVP 方案
- 部署链路未完全统一
- 测试体系不足
- 合规文案未形成上线最终版本

## 5. 开工阶段要求

当前执行板应与 [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md) 保持一致。

开工顺序要求：

- 后端先完成认证、数据库迁移、任务模型和接口骨架
- 前端并行搭页面壳体和统一状态层，但不得抢跑接口结构
- 测试从第一周开始建立 smoke 与认证/异常样本

第一阶段的核心不是“功能齐全”，而是先把以下四条主线做稳：

- 认证和权限
- 分析任务与结果结构
- 失败与降级状态
- 复盘任务闭环

## 6. 第一周与第二周交付要求

### 第一周必须交付

后端：

- 数据库迁移可跑通
- 认证方案定稿并有实现骨架
- API 错误响应统一
- `analysis_tasks / analysis_results` 核心模型落地

前端：

- 页面壳体和路由可跑通
- API 客户端层建好
- 统一错误态和加载态组件建好
- 登录态守卫建好

测试：

- 第一版 smoke 清单
- 第一版认证与异常用例
- 第一版联调数据样本

### 第二周必须交付

后端：

- 画像、股票搜索、分析任务创建接口可用
- 结果查询接口可返回基础结构
- 复盘任务自动生成链路打通

前端：

- 画像页、输入页、结果页可联调
- `processing / ready / failed / expired` 状态可正确渲染

测试：

- 主流程 smoke 跑第一轮
- 401/403、失败态、过期态开始验证

## 7. 任务状态定义

- `todo`：未开始
- `in_progress`：进行中
- `blocked`：被前置条件或风险阻塞
- `done`：已完成
- `accepted`：已验收通过
- `deferred`：延期，不进入当前版本

## 8. 优先级定义

- `P0`：必须完成，否则不进入内测/灰度
- `P1`：强烈建议完成，否则质量明显不足
- `P2`：可延后
- `P3`：当前版本不做

## 9. 角色定义

- 产品负责人：范围、文案、指标、验收、上线判断
- 前端负责人：页面流程、状态管理、交互、埋点、异常态
- 后端负责人：接口、数据、分析链路、认证、监控、部署
- 测试负责人：smoke、回归、异常场景验证
- 运营负责人：内测招募、用户反馈、FAQ、话术
- 合规协同：边界审查、文案审核、协议与政策检查

## 10. 阶段一任务板：P0 收口与修基础

### 10.1 产品负责人

#### TASK-PM-001
- 任务：冻结 v1 功能范围
- 优先级：P0
- 状态：todo
- 前置条件：无
- 阻塞性质：上线阻塞
- 交付物：v1 功能清单定稿
- 验收标准：
  - 明确哪些功能上线
  - 明确哪些功能弱化
  - 明确哪些功能不做

#### TASK-PM-002
- 任务：统一对外产品定位与禁用词
- 优先级：P0
- 状态：todo
- 前置条件：v1 功能范围冻结
- 阻塞性质：上线阻塞
- 交付物：对外口径清单
- 验收标准：
  - 所有关键页面和宣传文案有统一口径
  - 明确禁用词和替代表达

#### TASK-PM-003
- 任务：确认观察列表上线策略
- 优先级：P0
- 状态：todo
- 前置条件：当前闭环现状评估完成
- 阻塞性质：主流程阻塞
- 交付物：观察列表决策说明
- 验收标准：
  - 明确保留、弱化或隐藏
  - 团队内部无歧义

#### TASK-PM-004
- 任务：完成风险声明与结果页边界文案审校
- 优先级：P0
- 状态：todo
- 前置条件：产品边界明确
- 阻塞性质：上线阻塞
- 交付物：结果页文案终版
- 验收标准：
  - 无直接买卖暗示
  - 风险提示清晰
  - 数据不足降级表达清晰

#### TASK-PM-005
- 任务：冻结执行基线文档并发布阅读顺序
- 优先级：P0
- 状态：todo
- 前置条件：文档总索引已完成
- 阻塞性质：执行阻塞
- 基线文档：
  - [investment_document_master_index.md](F:/investment/structure/investment_document_master_index.md)
  - [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
  - [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
- 交付物：执行基线清单与角色阅读顺序
- 验收标准：
  - 产品、前端、后端、测试、运营都知道先读哪些文档
  - 团队不再并行使用互相冲突的口头版本

### 10.2 前端负责人

#### TASK-FE-001
- 任务：修复前端乱码与文案不统一问题
- 优先级：P0
- 状态：todo
- 前置条件：产品文案终稿
- 阻塞性质：上线阻塞
- 交付物：前端统一文案版本
- 验收标准：
  - 无乱码
  - 页面文案统一
  - 无高风险表达残留

#### TASK-FE-002
- 任务：统一主流程异常态、失败态、加载态
- 优先级：P0
- 状态：todo
- 前置条件：接口错误规范明确
- 阻塞性质：主流程阻塞
- 交付物：状态规范实现
- 验收标准：
  - 分析中、失败、数据不足、未登录场景均可正确反馈
  - 用户不会看到无意义空白状态
  - 与异常降级基线文档一致

#### TASK-FE-003
- 任务：结果页补齐“数据不足 / 重新评估 / 过期”可见状态
- 优先级：P0
- 状态：todo
- 前置条件：后端状态定义明确
- 阻塞性质：主流程阻塞
- 交付物：结果页状态增强版
- 验收标准：
  - 用户能理解为什么当前不能继续判断
  - 过期结果不会被误认为仍然有效

#### TASK-FE-004
- 任务：统一登录态、未登录跳转和会话失效反馈
- 优先级：P1
- 状态：todo
- 前置条件：后端认证逻辑收口
- 阻塞性质：体验阻塞
- 交付物：登录态交互完善版
- 验收标准：
  - token 失效有清晰反馈
  - 未登录访问被正确拦截
  - 登录成功后跳转路径正确

#### TASK-FE-005
- 任务：按统一 API 契约调整前端请求与状态映射
- 优先级：P0
- 状态：todo
- 前置条件：API 契约冻结
- 阻塞性质：主流程阻塞
- 基线文档：
  - [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
  - [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
  - [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
- 交付物：前端接口映射收口版
- 验收标准：
  - 前端状态字段不再自行扩展非契约枚举
  - 401、403、failed、expired、degraded 展示一致
  - 结果页主卡与 API 返回结构一致

#### TASK-FE-006
- 任务：按开工清单完成页面壳体、路由和统一状态组件
- 优先级：P0
- 状态：todo
- 前置条件：执行基线冻结
- 阻塞性质：联调阻塞
- 基线文档：
  - [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md)
  - [ai_investment_decision_system_ui_structure_design.md](F:/investment/structure/ai_investment_decision_system_ui_structure_design.md)
- 交付物：前端第一周开工版
- 验收标准：
  - 登录页、画像页、首页、输入页、结果页壳体可访问
  - 加载态、失败态、过期态组件可复用
  - 登录态守卫已建立

### 10.3 后端负责人

#### TASK-BE-001
- 任务：关闭开发态 debug 用户回退逻辑
- 优先级：P0
- 状态：todo
- 前置条件：正式认证策略确定
- 阻塞性质：上线阻塞
- 交付物：无 debug 放行版本
- 验收标准：
  - 无 token 不再默认返回测试用户
  - 不再自动放行测试账号

#### TASK-BE-002
- 任务：关闭启动时自动创建测试用户逻辑
- 优先级：P0
- 状态：todo
- 前置条件：认证流程收口
- 阻塞性质：上线阻塞
- 交付物：生产可用启动逻辑
- 验收标准：
  - 启动过程不自动注入测试身份
  - 启动失败有明确日志

#### TASK-BE-003
- 任务：统一 API 错误返回格式
- 优先级：P0
- 状态：todo
- 前置条件：前端错误展示需求明确
- 阻塞性质：主流程阻塞
- 交付物：统一错误响应规范
- 验收标准：
  - 常见错误状态格式一致
  - 前端可稳定消费

#### TASK-BE-004
- 任务：补强外部数据源超时、失败、降级策略
- 优先级：P0
- 状态：todo
- 前置条件：降级规则定义完成
- 阻塞性质：上线阻塞
- 交付物：数据源容错增强版
- 验收标准：
  - 外部接口异常时不输出误导性结果
  - 数据不足会触发明确降级

#### TASK-BE-005
- 任务：修复 Docker 构建链路与真实依赖不一致问题
- 优先级：P0
- 状态：todo
- 前置条件：部署方案确认
- 阻塞性质：上线阻塞
- 交付物：可用的容器化部署链路
- 验收标准：
  - Docker 构建成功
  - 与当前依赖方式一致
  - 文档与实际执行一致

#### TASK-BE-006
- 任务：按生产架构拆分 API、Worker、数据聚合边界
- 优先级：P0
- 状态：todo
- 前置条件：生产系统架构冻结
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
- 交付物：模块边界说明与服务拆分实施方案
- 验收标准：
  - 分析执行链路异步化
  - API 不直接承载重分析任务
  - 外部数据调用被明确隔离

#### TASK-BE-007
- 任务：落地正式认证、资源级鉴权与会话收口
- 优先级：P0
- 状态：todo
- 前置条件：认证方案冻结
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
- 交付物：认证与鉴权收口版
- 验收标准：
  - 无 token 不再放行
  - 用户只能访问自己的数据
  - 刷新会话、401、403 处理统一

#### TASK-BE-008
- 任务：落实异常分类、降级标记与统一状态枚举
- 优先级：P0
- 状态：todo
- 前置条件：异常降级方案冻结
- 阻塞性质：主流程阻塞
- 基线文档：
  - [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
  - [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
- 交付物：状态枚举与降级字段收口版
- 验收标准：
  - 外部数据失败不会产出强结论
  - 任务状态与前端展示口径一致
  - 错误码、降级原因、日志字段可追踪

#### TASK-BE-009
- 任务：修正数据库、类型、迁移文件的一致性冲突
- 优先级：P0
- 状态：todo
- 前置条件：API 契约收口完成
- 阻塞性质：实现阻塞
- 基线文档：
  - [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
  - [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
- 交付物：实现一致性修正版
- 验收标准：
  - PostgreSQL 口径统一
  - UUID 生成方案统一
  - 生产迁移中无测试用户 seed
  - 类型、迁移、设计文档枚举一致

#### TASK-BE-010
- 任务：落地最小安全与数据治理控制
- 优先级：P0
- 状态：todo
- 前置条件：安全方案冻结
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
- 交付物：最小安全控制实现版
- 验收标准：
  - token 和敏感字段不明文落日志
  - 数据访问权限按角色收口
  - 备份、删除、脱敏口径明确

#### TASK-BE-011
- 任务：按开工清单完成数据库迁移、任务模型与接口骨架
- 优先级：P0
- 状态：todo
- 前置条件：数据库与契约基线冻结
- 阻塞性质：联调阻塞
- 基线文档：
  - [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md)
  - [database_design.md](F:/investment/structure/database_design.md)
  - [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md)
- 交付物：后端第一周开工版
- 验收标准：
  - 基础迁移可执行
  - `analysis_tasks / analysis_results` 核心模型落地
  - 创建分析和查询结果接口已有骨架
  - 错误响应结构可返回统一格式

#### TASK-BE-012
- 任务：落地数据库约束迁移与 JSON 结构对齐
- 优先级：P0
- 状态：todo
- 前置条件：基础 schema 已稳定
- 阻塞性质：实现阻塞
- 基线文档：
  - [investment_database_check_constraints_draft.md](F:/investment/structure/investment_database_check_constraints_draft.md)
  - [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md)
  - [migrations/005_check_constraints.sql](F:/investment/structure/migrations/005_check_constraints.sql)
- 交付物：约束迁移评估与实施版
- 验收标准：
  - 约束迁移可在测试环境验证
  - JSON 结构与类型定义一致
  - 不存在生产/dev seed 混用

### 10.4 测试负责人

#### TASK-QA-001
- 任务：建立手工 smoke checklist
- 优先级：P0
- 状态：todo
- 前置条件：v1 范围冻结
- 阻塞性质：上线阻塞
- 交付物：smoke checklist v1
- 验收标准：
  - 登录、搜索、分析、结果、记录、复盘、画像至少覆盖一遍

#### TASK-QA-002
- 任务：执行第一轮主流程 smoke
- 优先级：P0
- 状态：todo
- 前置条件：smoke checklist 完成
- 阻塞性质：主流程阻塞
- 交付物：smoke 结果清单
- 验收标准：
  - 能明确指出阻塞项和优先修复项

#### TASK-QA-003
- 任务：建立基于异常与认证基线的专项验证集
- 优先级：P0
- 状态：todo
- 前置条件：异常与认证文档冻结
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
  - [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
  - [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)
- 交付物：认证与降级专项测试集
- 验收标准：
  - 401/403、token 失效、数据不足、外部失败、分析超时均有用例
  - 结果页不会把降级结果误当正常结果

#### TASK-QA-004
- 任务：按开工清单建立第一周 smoke 与联调用例包
- 优先级：P0
- 状态：todo
- 前置条件：开工基线已冻结
- 阻塞性质：联调阻塞
- 基线文档：
  - [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md)
- 交付物：第一周测试开工包
- 验收标准：
  - smoke 用例、认证异常用例、联调样本三者齐备
  - 后端和前端使用同一批样本

### 10.5 运营负责人

#### TASK-OPS-001
- 任务：准备内测 FAQ 和首屏教育文案
- 优先级：P1
- 状态：todo
- 前置条件：产品边界口径确认
- 阻塞性质：认知风险阻塞
- 交付物：FAQ 文档
- 验收标准：
  - 能回答“这是不是荐股工具”
  - 能回答“为什么不给我直接答案”

#### TASK-OPS-002
- 任务：建立内测反馈收集渠道
- 优先级：P1
- 状态：todo
- 前置条件：内测方案确定
- 阻塞性质：反馈阻塞
- 交付物：反馈群 / 表单 / 归档模板
- 验收标准：
  - 反馈收集有统一入口
  - 可追踪问题来源与优先级

#### TASK-OPS-003
- 任务：建立误解风险与投诉升级口径
- 优先级：P0
- 状态：todo
- 前置条件：合规与边界文档冻结
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_risk_and_compliance_brief.md](F:/investment/structure/investment_risk_and_compliance_brief.md)
  - [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)
- 交付物：统一应答话术与升级流程
- 验收标准：
  - “是不是荐股工具”“为什么不直接告诉我买卖”有统一答复
  - 高风险投诉有升级路径
  - 重大误解可归档和回溯

## 11. 阶段二任务板：P1 闭环与内测能力

### 11.1 产品负责人

#### TASK-PM-101
- 任务：定义关注理由与复盘的闭环规则
- 优先级：P1
- 状态：todo
- 前置条件：观察列表策略明确
- 阻塞性质：闭环阻塞
- 交付物：闭环规则说明
- 验收标准：
  - 关注理由能服务复盘
  - 不形成额外复杂度负担

#### TASK-PM-102
- 任务：定义最小事件埋点清单
- 优先级：P1
- 状态：todo
- 前置条件：核心流程稳定
- 阻塞性质：数据验证阻塞
- 交付物：埋点文档
- 验收标准：
  - 覆盖登录、发起分析、到达结果、记录理由、进入复盘等核心节点

#### TASK-PM-103
- 任务：建立基线文档变更评审机制
- 优先级：P1
- 状态：todo
- 前置条件：执行基线已冻结
- 阻塞性质：收口阻塞
- 交付物：文档变更评审规则
- 验收标准：
  - 涉及 PRD、架构、认证、异常、安全、API 的修改必须留痕
  - 不再出现实现先改、文档后补的失控模式

### 11.2 前端负责人

#### TASK-FE-101
- 任务：观察列表改为服务端优先
- 优先级：P1
- 状态：todo
- 前置条件：后端接口稳定
- 阻塞性质：闭环阻塞
- 交付物：服务端观察列表接入版
- 验收标准：
  - 跨设备可见
  - 不再主要依赖本地存储

#### TASK-FE-102
- 任务：接入埋点和关键转化统计
- 优先级：P1
- 状态：todo
- 前置条件：埋点文档完成
- 阻塞性质：数据验证阻塞
- 交付物：埋点接入版
- 验收标准：
  - 核心页面和关键动作有追踪

#### TASK-FE-103
- 任务：优化首页回流入口
- 优先级：P1
- 状态：todo
- 前置条件：记录页和复盘页逻辑稳定
- 阻塞性质：留存阻塞
- 交付物：首页回流优化版
- 验收标准：
  - 最近分析、待复盘、画像摘要能明显促进二次使用

### 11.3 后端负责人

#### TASK-BE-101
- 任务：观察列表与关注理由服务端闭环
- 优先级：P1
- 状态：todo
- 前置条件：产品规则明确
- 阻塞性质：闭环阻塞
- 交付物：服务端持久化版本
- 验收标准：
  - 关注理由可查询
  - 观察列表跨会话持久化

#### TASK-BE-102
- 任务：补充健康检查、日志可追踪、关键失败监控
- 优先级：P1
- 状态：todo
- 前置条件：部署口径统一
- 阻塞性质：灰度阻塞
- 交付物：最小可观测性版本
- 验收标准：
  - 核心分析链路失败能快速定位
  - 健康检查和关键日志可查看

#### TASK-BE-103
- 任务：建立最小测试基线
- 优先级：P1
- 状态：todo
- 前置条件：接口收口
- 阻塞性质：质量阻塞
- 交付物：关键接口测试集
- 验收标准：
  - 至少覆盖登录、画像、分析、记录、复盘、观察列表

#### TASK-BE-104
- 任务：补齐关键接口分页、幂等和 JSON 结构约束
- 优先级：P1
- 状态：todo
- 前置条件：核心接口收口
- 阻塞性质：质量阻塞
- 基线文档：
  - [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
- 交付物：接口约束增强版
- 验收标准：
  - 列表接口有统一分页协议
  - 核心写接口具备幂等保护
  - JSON 扩展字段结构受控

### 11.4 测试负责人

#### TASK-QA-101
- 任务：建立关键流程回归清单
- 优先级：P1
- 状态：todo
- 前置条件：主流程稳定
- 阻塞性质：质量阻塞
- 交付物：回归用例集
- 验收标准：
  - 每次发版前可快速验证关键路径

#### TASK-QA-102
- 任务：补异常场景测试
- 优先级：P1
- 状态：todo
- 前置条件：异常态定义清楚
- 阻塞性质：稳定性阻塞
- 交付物：异常验证报告
- 验收标准：
  - 数据不足、网络失败、token 失效等场景都可验证

### 11.5 运营负责人

#### TASK-OPS-101
- 任务：准备 Alpha 用户池和访谈计划
- 优先级：P1
- 状态：todo
- 前置条件：内测版本可用
- 阻塞性质：内测阻塞
- 交付物：Alpha 名单与访谈排期
- 验收标准：
  - 第一批用户具备代表性
  - 可支持快速反馈

#### TASK-OPS-102
- 任务：搭建每周反馈归档机制
- 优先级：P1
- 状态：todo
- 前置条件：反馈渠道建立
- 阻塞性质：反馈阻塞
- 交付物：反馈台账
- 验收标准：
  - 所有用户反馈可归档、分类、追踪

## 12. 阶段三任务板：灰度准备与上线判断

### 12.1 产品负责人

#### TASK-PM-201
- 任务：建立 Go / No-Go 评审机制
- 优先级：P0
- 状态：todo
- 前置条件：内测数据形成
- 阻塞性质：上线阻塞
- 交付物：评审模板
- 验收标准：
  - 是否上线有明确判断标准
  - 不靠主观感觉决策

#### TASK-PM-202
- 任务：输出灰度版本结论报告
- 优先级：P0
- 状态：todo
- 前置条件：Beta 数据汇总完成
- 阻塞性质：上线阻塞
- 交付物：灰度结论报告
- 验收标准：
  - 明确是否可灰度
  - 明确主要风险和后续动作

### 12.2 前端负责人

#### TASK-FE-201
- 任务：补灰度上线前最小埋点看板所需前端数据
- 优先级：P1
- 状态：todo
- 前置条件：埋点方案落实
- 阻塞性质：灰度阻塞
- 交付物：前端指标数据完整版本
- 验收标准：
  - 分析漏斗和关键行为节点可追踪

### 12.3 后端负责人

#### TASK-BE-201
- 任务：建立发布、回滚、值守支持所需能力
- 优先级：P0
- 状态：todo
- 前置条件：部署方式确定
- 阻塞性质：上线阻塞
- 交付物：发布与回滚方案
- 验收标准：
  - 可快速发布
  - 可快速回滚
  - 可定位核心问题

#### TASK-BE-202
- 任务：完成备份恢复与审计留痕闭环
- 优先级：P0
- 状态：todo
- 前置条件：安全治理能力具备
- 阻塞性质：上线阻塞
- 基线文档：
  - [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
  - [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)
- 交付物：备份恢复与审计方案
- 验收标准：
  - 每日备份可执行
  - 恢复步骤可演练
  - 高风险管理操作可追踪

### 12.4 测试负责人

#### TASK-QA-201
- 任务：执行灰度前最终回归
- 优先级：P0
- 状态：todo
- 前置条件：版本冻结
- 阻塞性质：上线阻塞
- 交付物：最终回归结论
- 验收标准：
  - 核心功能通过
  - 已知风险清单可接受

### 12.5 运营负责人

#### TASK-OPS-201
- 任务：准备灰度用户池和统一口径
- 优先级：P0
- 状态：todo
- 前置条件：Go / No-Go 通过
- 阻塞性质：上线阻塞
- 交付物：灰度执行清单
- 验收标准：
  - 灰度用户池准备好
  - FAQ、客服、反馈口径一致

## 13. 联调前阻塞项

以下事项未完成前，不建议进入大范围联调：

- 认证逻辑仍带开发态放行
- API 返回结构未收口
- 任务状态枚举未统一
- 数据库迁移仍混有生产/开发数据
- 结果页错误态还没有明确口径

## 14. 内测前阻塞项

以下事项未完成前，不建议进入真实内测：

- 用户只能访问自己的数据还未验证
- 数据不足场景仍可能输出强结论
- 结果页过期态未完成
- 复盘任务无法稳定生成
- 日志无法按 `analysis_id` 追踪
- 关键告警还未建立

## 15. 阻塞项清单

以下事项如未关闭，不建议进入灰度：

- 开发态认证逻辑未关闭
- 产品边界文案未统一
- 数据不足时仍可能输出强结论
- 主流程 smoke 未通过
- 日志和监控不可用
- 发布与回滚方案缺失
- 用户误解率过高
- 观察列表策略未决
- API 契约与实现口径未统一
- 安全与数据治理底线未落地
- 数据库与迁移仍混有开发态口径
- 异常降级规则未形成一致实现

## 16. 周推进机制

每周固定执行：

- 周一：确认本周目标
- 周二到周四：执行核心任务
- 周五：汇报本周状态并检查基线文档是否被破坏
- 周五输出：
  - 本周完成项
  - 本周阻塞项
  - 本周新增风险
  - 下周优先任务
  - 本周涉及的基线文档变更
  - 本周新增的一致性冲突

## 17. 验收机制

每个阶段结束时，必须做阶段验收。

### 阶段一验收

重点看：

- 产品范围是否冻结
- 开发态逻辑是否关闭
- 文案与边界是否统一
- smoke 是否通过
- 架构、认证、异常、安全、API 基线是否进入执行状态
- 第一周、第二周开工交付是否完成

### 阶段二验收

重点看：

- 观察列表和关注理由是否闭环
- 行为埋点是否到位
- Alpha / Beta 是否形成有效反馈
- 关键回归是否可执行
- 文档变更是否受控
- 实现与基线是否仍一致

### 阶段三验收

重点看：

- 是否具备灰度条件
- 是否具备回滚能力
- 是否具备值守和应急能力
- 是否已完成上线检查
- 备份恢复和审计是否可执行

## 18. 最终建议

这个任务板的目的不是“把工作排满”，而是让团队始终围绕同一个核心问题推进：

在不越过产品和合规边界的前提下，把 AI 投资决策助手做成一个真正可用、可信、可内测、可灰度的产品。
