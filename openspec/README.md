# OpenSpec 治理说明

更新时间：2026-03-30

## 1. 定位

`openspec/` 是本项目的规格治理层，用来管理两类内容：

- 顶层 baseline specs：描述“目标产品能力基线”
- future changes：描述“对 baseline 的新增或修改”

它不替代 `structure/`，而是和 `structure/` 形成双轨治理：

- `structure/` 负责长文基线，保存产品、架构、数据库、路线图、执行板等完整分析文档
- `openspec/` 负责把这些长文基线压缩成可验证、可变更、可追踪的 baseline specs 和 change artifacts

其中 baseline specs 在语义上分为两层：

- 业务稳定层 specs：描述长期成立的用户价值、业务边界和场景闭环
- 共享协议与治理 specs：描述跨场景共用的访问边界、错误响应、状态口径、结果结构和安全底线

实现方案、技术选型、代码路径、接口挂载方式、环境变量装配和迁移步骤不属于 baseline spec 主体，应优先放在 change 的 `design.md` 和 `tasks.md`。

## 2. 目录约定

```text
openspec/
├── config.yaml                         # OpenSpec 项目级配置
├── README.md                           # 本说明
├── specs/                              # 顶层 baseline specs（含业务层与共享层）
│   └── <capability>/spec.md
└── changes/
    ├── <change-id>/
    │   ├── proposal.md
    │   ├── design.md
    │   ├── specs/<capability>/spec.md
    │   └── tasks.md
    └── archive/                        # 只通过 `openspec archive` 维护
```

约定：

- capability 目录名统一使用英文 kebab-case
- 正文统一使用中文
- 顶层 baseline specs 使用 `## Purpose` + `## Requirements`；change delta specs 使用 `ADDED / MODIFIED / REMOVED / RENAMED`
- `changes/archive/` 只通过 `openspec archive` 维护，不手工搬运或重命名
- baseline specs 可以表达稳定业务语义，也可以表达跨场景共享 contract，但不应直接绑定当前代码文件、具体路由、框架中间件、环境变量名或局部重构方案

## 3. Baseline Spec Taxonomy

### 3.1 业务稳定层 Specs

| Spec | 目标范围 | 主要来源文档 |
| --- | --- | --- |
| `user-profile` | 用户画像字段、枚举、读写边界、快照使用约束 | `investment_api_contract_and_implementation_alignment.md`、`investment_json_schema_contract.md`、`database_design.md` |
| `single-stock-analysis` | 单股咨询输入、任务状态、决策卡、有效期 | `investment_v1_prd.md`、`investment_api_contract_and_implementation_alignment.md`、`investment_json_schema_contract.md` |
| `pre-trade-check` | 交易前自检输入、行为干预优先级、风险提示 | `investment_v1_prd.md`、`investment_error_handling_and_degradation_strategy.md`、`investment_json_schema_contract.md` |
| `post-trade-review` | 交易后复盘输入、归因、改进动作、复盘触发 | `investment_v1_prd.md`、`investment_json_schema_contract.md`、`investment_beta_plan.md` |
| `watchlist-and-focus` | 观察列表、关注理由、跨设备持久化、一致性 | `investment_engineering_kickoff_checklist.md`、`investment_team_execution_board.md`、`investment_current_implementation_gap_audit.md` |
| `history-and-review-loop` | 历史记录查询、结果回看、复盘任务生命周期 | `investment_product_roadmap_12_weeks.md`、`investment_beta_plan.md`、`investment_api_contract_and_implementation_alignment.md` |

### 3.2 共享协议与治理 Specs

| Spec | 目标范围 | 主要来源文档 |
| --- | --- | --- |
| `auth-session` | 访问身份、资源归属、会话有效性、真实环境与开发便利能力隔离 | `investment_auth_and_authorization_design.md`、`investment_security_and_data_governance_minimum_plan.md`、`investment_current_implementation_gap_audit.md` |
| `platform-contracts` | 统一错误模型、状态口径、关键结果结构、降级表达与安全治理底线 | `investment_api_contract_and_implementation_alignment.md`、`investment_json_schema_contract.md`、`investment_error_handling_and_degradation_strategy.md`、`investment_security_and_data_governance_minimum_plan.md` |

说明：

- 当前仓库为兼容现有 change 和工具约束，继续沿用 `auth-session`、`platform-contracts` 作为目录名
- 它们在语义上属于共享基线 spec，而不是单独的业务 capability
- 如果后续需要拆分为更细的 `identity-and-access`、`error-status-contract`、`security-governance` 等 spec，应通过独立 change 迁移，而不是直接重命名目录

## 4. 工作流

### 4.1 什么时候直接改 baseline specs

仅在以下情况直接修改 `openspec/specs/`：

- 初始化基线能力
- 通过 `openspec archive <change-id>` 把已完成 change 合并回主线

除这两种情况外，不直接编辑 baseline specs。

### 4.2 什么时候创建 change

任何会改变 capability requirement 的工作，都必须先创建 change：

```powershell
openspec new change <change-id>
```

建议命名：

- `p0-auth-production-hardening`
- `p1-watchlist-persistence`
- `p2-test-release-gates`

change workflow 固定为：

1. `proposal.md`：为什么做、改什么、影响什么
2. `specs/<capability>/spec.md`：新增或修改 requirements
3. `design.md`：如何落地，以及和当前实现差距
4. `tasks.md`：可执行任务清单

### 4.3 什么时候参考 `structure/`

所有 OpenSpec 产物都必须参考 `structure/` 中的长文基线：

- PRD / UI / 路线图决定“做什么”和“优先级”
- 架构 / 认证 / 异常 / 安全 / API / 数据库文档决定“能力边界”
- `investment_team_execution_board.md` 决定“任务如何落板”
- `investment_current_implementation_gap_audit.md` 决定“先补哪条差距”

## 5. Initial Change Backlog

以下 backlog 用来把现有代码逐步收口到 baseline specs：

| Change ID | 目标 | 关联 capability |
| --- | --- | --- |
| `p0-auth-production-hardening` | 关闭 debug fallback、去掉运行时测试用户、收紧生产安全配置 | `auth-session`、`platform-contracts` |
| `p0-align-analysis-api-contract` | 对齐分析场景 contract、状态枚举、错误结构 | `single-stock-analysis`、`pre-trade-check`、`post-trade-review`、`platform-contracts` |
| `p0-runtime-config-startup-cleanup` | 收紧启动校验、环境隔离、运行时配置边界 | `platform-contracts` |
| `p1-watchlist-persistence` | 让观察列表和关注理由完成服务端持久化闭环 | `watchlist-and-focus` |
| `p1-review-loop-closed-loop` | 把结果回看、复盘任务和历史查询收成长期闭环 | `history-and-review-loop`、`post-trade-review` |
| `p2-test-release-gates` | 建立关键回归、发布前门禁、验收清单映射 | `platform-contracts` |

本轮已经附带创建 `p0-auth-production-hardening` 作为种子 change，用来验证 OpenSpec 工作流可用。

## 6. 常用校验命令

```powershell
openspec list --specs
openspec validate --specs --strict
openspec status --change p0-auth-production-hardening
openspec validate p0-auth-production-hardening --type change --strict
```

完成一个 change 后，使用以下命令归档：

```powershell
openspec archive <change-id>
```

归档后要确认两件事：

- 顶层 `openspec/specs/` 已吸收变更
- `openspec/changes/<change-id>/` 已进入 `openspec/changes/archive/`
