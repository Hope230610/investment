# AI 投资决策助手 文档总索引

更新时间：2026-03-30

## 1. 文档目的

本索引用于把 `F:\investment\structure` 中现有文档整合为一套可执行的产品落地文档体系。

目标不是重复写一遍所有内容，而是回答以下问题：

- 每份文档解决什么问题
- 文档之间是什么关系
- 先看什么、后看什么
- 哪些文档是产品决策基线
- 哪些文档是研发落地基线
- 哪些文档是上线前必须对齐的基线

## 2. 当前文档体系总览

当前 `structure` 中的文档已经可以分成 6 层：

1. 产品定义层
2. 版本推进层
3. 落地设计层
4. 工程实现层
5. 风险与上线层
6. 执行协同层

新补充的 5 份文档，主要补齐的是第 3 层和第 4 层之间原本缺失的“从产品到工程”的桥梁。

## 3. 一层：产品定义层

这层回答“我们做的到底是什么产品”。

### 核心文档

- [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
- [investment_mvp_feature_priority_matrix.md](F:/investment/structure/investment_mvp_feature_priority_matrix.md)
- [ai_investment_decision_system_ui_structure_design.md](F:/investment/structure/ai_investment_decision_system_ui_structure_design.md)

### 职责划分

`investment_v1_prd.md`

- 定义产品定位
- 定义目标用户
- 定义三大核心场景
- 定义输出边界和成功指标

`investment_mvp_feature_priority_matrix.md`

- 把 PRD 中的需求收口为 `P0/P1/P2/P3`
- 防止范围失控

`ai_investment_decision_system_ui_structure_design.md`

- 把 PRD 的场景、页面、结果页结构转成可设计、可开发的 UI 结构

### 使用原则

- 所有新增需求先回到 PRD 判断是否属于 v1
- 所有功能优先级争议先回到优先级矩阵判断
- 所有页面和交互设计先回到 UI 结构文档判断是否符合主链路

## 4. 二层：版本推进层

这层回答“这个产品按什么节奏推进到可上线”。

### 核心文档

- [investment_product_roadmap_12_weeks.md](F:/investment/structure/investment_product_roadmap_12_weeks.md)
- [investment_beta_plan.md](F:/investment/structure/investment_beta_plan.md)
- [investment_metrics_dashboard.md](F:/investment/structure/investment_metrics_dashboard.md)

### 职责划分

`investment_product_roadmap_12_weeks.md`

- 定义 12 周推进阶段
- 定义每周目标、交付物、成功标准

`investment_beta_plan.md`

- 定义 Alpha、Beta 1、Beta 2 的验证对象、任务、指标和门槛

`investment_metrics_dashboard.md`

- 定义指标体系
- 规定产品是否成立、是否进入下一阶段的判断依据

### 使用原则

- 路线图是排期基线
- Beta 方案是验证基线
- 指标看板是决策基线

## 5. 三层：落地设计层

这层回答“如何把产品真正设计成一个可开发、可联调、可内测的系统”。

### 核心文档

- [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
- [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
- [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
- [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
- [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)

### 这 5 份文档分别解决什么问题

`investment_production_system_architecture.md`

- 定义生产系统模块
- 定义核心数据流
- 定义异步边界
- 定义部署和可观测性原则

`investment_auth_and_authorization_design.md`

- 定义登录、token、会话、鉴权和资源归属边界
- 关闭开发态身份逻辑

`investment_error_handling_and_degradation_strategy.md`

- 定义异常分类
- 定义任务状态
- 定义降级等级
- 定义前端状态和用户文案映射

`investment_security_and_data_governance_minimum_plan.md`

- 定义数据分类
- 定义访问控制、脱敏、留存、删除、备份底线

`investment_api_contract_and_implementation_alignment.md`

- 统一 API、数据库、类型、迁移、状态枚举的实现口径
- 标出当前文档与实现中的冲突点

### 与产品定义层的关系

- PRD 定义“要做什么”
- 这 5 份文档定义“怎么把它稳定做出来”

### 与工程实现层的关系

- 这 5 份文档是研发开始真正收口实现前必须阅读的桥接层

## 6. 四层：工程实现层

这层回答“数据结构和实现基础是否能支撑产品方案”。

### 核心文档

- [database_design.md](F:/investment/structure/database_design.md)
- [db_types.ts](F:/investment/structure/db_types.ts)
- [investment_database_check_constraints_draft.md](F:/investment/structure/investment_database_check_constraints_draft.md)
- [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md)
- [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md)
- [investment_current_implementation_gap_audit.md](F:/investment/structure/investment_current_implementation_gap_audit.md)
- [migrations/README.md](F:/investment/structure/migrations/README.md)
- [migrations/001_init_schema.sql](F:/investment/structure/migrations/001_init_schema.sql)
- [migrations/002_init_data.sql](F:/investment/structure/migrations/002_init_data.sql)
- [migrations/003_triggers.sql](F:/investment/structure/migrations/003_triggers.sql)

### 当前定位

这部分已经具备“实现底稿”的雏形，但还不是完全收口状态。

主要原因：

- 仍有部分口径不一致
- 仍有 dev/prod 混写问题
- 仍缺少正式 API 契约驱动

其中：

- [database_design.md](F:/investment/structure/database_design.md) 定义数据结构与字段规则
- [db_types.ts](F:/investment/structure/db_types.ts) 定义应用层类型边界
- [investment_database_check_constraints_draft.md](F:/investment/structure/investment_database_check_constraints_draft.md) 定义建议优先落库的 SQL 级约束草案
- [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md) 定义关键 JSON 结构合同
- [investment_engineering_kickoff_checklist.md](F:/investment/structure/investment_engineering_kickoff_checklist.md) 定义研发正式开工顺序与第一阶段交付
- [investment_current_implementation_gap_audit.md](F:/investment/structure/investment_current_implementation_gap_audit.md) 定义真实代码与当前文档基线的差距审查

### 工程层使用原则

- 数据库设计必须服从 PRD 和 API 契约
- 类型定义必须服从数据库和接口枚举
- 迁移文件必须区分 `schema`、`seed`、`dev seed`

## 7. 五层：风险与上线层

这层回答“产品什么时候能安全进入真实用户环境”。

### 核心文档

- [investment_risk_and_compliance_brief.md](F:/investment/structure/investment_risk_and_compliance_brief.md)
- [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)

### 职责划分

`investment_risk_and_compliance_brief.md`

- 定义产品边界、宣传边界、AI 输出边界、画像边界、监管风险

`investment_release_checklist.md`

- 定义上线前的产品、技术、数据、质量、监控、运营、应急检查项

### 与三层文档的衔接

- 合规简报定义“哪些不能越线”
- 架构、认证、异常、安全文档定义“如何从系统设计上避免越线”

## 8. 六层：执行协同层

这层回答“团队如何照着上面这些文档推进”。

### 核心文档

- [investment_team_execution_board.md](F:/investment/structure/investment_team_execution_board.md)

### 当前作用

- 把产品、前端、后端、测试、运营拆成可执行任务
- 标明阻塞项、优先级、验收标准

### 建议使用方式

- 以后所有任务新增，先对照总索引找基线文档
- 再回填到执行板，而不是直接拍脑袋加任务

## 9. 阅读顺序建议

### 9.1 产品负责人

建议顺序：

1. [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
2. [investment_mvp_feature_priority_matrix.md](F:/investment/structure/investment_mvp_feature_priority_matrix.md)
3. [investment_product_roadmap_12_weeks.md](F:/investment/structure/investment_product_roadmap_12_weeks.md)
4. [investment_beta_plan.md](F:/investment/structure/investment_beta_plan.md)
5. [investment_metrics_dashboard.md](F:/investment/structure/investment_metrics_dashboard.md)
6. [investment_risk_and_compliance_brief.md](F:/investment/structure/investment_risk_and_compliance_brief.md)
7. [investment_team_execution_board.md](F:/investment/structure/investment_team_execution_board.md)

### 9.2 前端负责人

建议顺序：

1. [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
2. [ai_investment_decision_system_ui_structure_design.md](F:/investment/structure/ai_investment_decision_system_ui_structure_design.md)
3. [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
4. [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
5. [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
6. [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)

### 9.3 后端负责人

建议顺序：

1. [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
2. [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
3. [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
4. [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
5. [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
6. [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
7. [database_design.md](F:/investment/structure/database_design.md)
8. [migrations/001_init_schema.sql](F:/investment/structure/migrations/001_init_schema.sql)

### 9.4 测试负责人

建议顺序：

1. [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
2. [investment_beta_plan.md](F:/investment/structure/investment_beta_plan.md)
3. [investment_metrics_dashboard.md](F:/investment/structure/investment_metrics_dashboard.md)
4. [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
5. [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)
6. [investment_team_execution_board.md](F:/investment/structure/investment_team_execution_board.md)

### 9.5 运营负责人

建议顺序：

1. [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
2. [investment_beta_plan.md](F:/investment/structure/investment_beta_plan.md)
3. [investment_risk_and_compliance_brief.md](F:/investment/structure/investment_risk_and_compliance_brief.md)
4. [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)
5. [investment_team_execution_board.md](F:/investment/structure/investment_team_execution_board.md)

## 10. 文档依赖关系

建议按下面的逻辑理解整套文档：

```text
PRD
→ MVP 优先级矩阵
→ UI 结构设计
→ 生产系统架构
→ 认证 / 异常降级 / 安全治理 / API 收口
→ 数据库与迁移
→ Beta 方案 / 指标看板
→ 发布清单 / 执行板
```

说明：

- `PRD` 是源头
- `执行板` 不是源头，而是所有前置文档对齐后的执行结果
- `发布清单` 不是设计文档，而是验收文档

## 11. 上线前必须锁定的基线文档

进入真实内测前，至少要把以下文档视为冻结基线：

- [investment_v1_prd.md](F:/investment/structure/investment_v1_prd.md)
- [investment_mvp_feature_priority_matrix.md](F:/investment/structure/investment_mvp_feature_priority_matrix.md)
- [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md)
- [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md)
- [investment_error_handling_and_degradation_strategy.md](F:/investment/structure/investment_error_handling_and_degradation_strategy.md)
- [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md)
- [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md)
- [investment_release_checklist.md](F:/investment/structure/investment_release_checklist.md)

## 12. 当前总索引给出的结论

当前 `structure` 已经不是一组零散分析文件，而是一套接近完整的产品落地文档体系。

其中：

- PRD、优先级、路线图、Beta、指标、合规、发布、执行板，构成了产品推进主线
- 新补的 5 份文档，补上了从“产品方案”到“工程落地”的桥梁
- 数据库、类型、迁移文件，构成实现基础，但仍需继续收口

## 13. 下一步建议

在已有总索引基础上，下一步最值得做的是两件事：

### 13.1 文档一致性收口

优先处理：

- [database_design.md](F:/investment/structure/database_design.md)
- [db_types.ts](F:/investment/structure/db_types.ts)
- [migrations/001_init_schema.sql](F:/investment/structure/migrations/001_init_schema.sql)
- [migrations/002_init_data.sql](F:/investment/structure/migrations/002_init_data.sql)
- [migrations/003_triggers.sql](F:/investment/structure/migrations/003_triggers.sql)

### 13.2 执行板映射升级

把新补的 5 份文档里的 `P0/P1` 要求回填到：

- [investment_team_execution_board.md](F:/investment/structure/investment_team_execution_board.md)

让执行板不只是任务列表，而是直接绑定新的架构、认证、异常、安全、API 基线。

## 14. 最终结论

这份总索引的作用，是把 `structure` 从“很多分析文档”变成“一套有层次、有依赖、有阅读顺序、有冻结基线的产品落地文档系统”。

后续无论是产品决策、研发推进、测试验收还是上线判断，都应先回到本索引定位基线文档，再开展具体工作。
