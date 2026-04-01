# AI 投资决策助手 研发开工清单

更新时间：2026-03-30

## 1. 文档目的

本清单用于把当前 `structure` 中已经形成的产品、架构、接口、数据库、约束文档，进一步压缩成一份面向研发真正可执行的开工包。

本清单重点回答：

- 研发开始前必须统一什么
- 后端先做什么
- 前端先做什么
- 测试先做什么
- 第一周必须产出什么
- 哪些事项未完成前，不应进入联调和内测

## 2. 开工前统一基线

研发正式开始前，团队必须先锁定以下基线文档：

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
- [migrations/005_check_constraints.sql](F:/investment/structure/migrations/005_check_constraints.sql)

要求：

- 任何实现如果和上述文档冲突，必须先修正文档或重新评审
- 不允许研发各自按口头理解开工

## 3. 角色开工顺序

### 3.1 后端先行

原因：

- 前端页面可先搭壳，但真正联调依赖认证、任务状态、结果结构、错误格式
- 当前产品的关键风险在于身份边界、异步任务、降级输出和结构化返回

### 3.2 前端并行但不抢跑

前端可并行做：

- 页面骨架
- 状态容器
- 契约类型对接
- 加载态/失败态/过期态 UI

前提：

- 不自己发明接口结构
- 不自己扩展状态枚举

### 3.3 测试从第一周介入

原因：

- 这不是普通信息产品，错误边界和误导风险很高
- 测试不能等到功能写完才开始

## 4. 后端开工清单

### 4.1 第一优先级模块

1. 认证与会话模块
2. 用户画像模块
3. 股票搜索模块
4. 分析任务模块
5. 分析结果查询模块
6. 复盘任务模块

### 4.2 后端第一阶段必须完成的能力

- 正式登录与鉴权中间件
- 资源归属校验
- 创建分析任务接口
- 查询分析任务结果接口
- 统一错误响应格式
- 基础数据库迁移落地
- 生产 seed 与 dev seed 分离

### 4.3 后端第一阶段建议交付顺序

#### 第 1 批

- 数据库基础迁移
- `pgcrypto` UUID 方案
- 基础表落库
- dev/prod seed 分层

#### 第 2 批

- 登录/会话/401/403
- 用户画像读写
- 股票搜索

#### 第 3 批

- 分析任务创建
- 分析状态查询
- 基础结果结构返回

#### 第 4 批

- 复盘任务生成与查询
- 观察列表与关注理由
- 行为埋点

## 5. 前端开工清单

### 5.1 第一优先级页面

- 登录页
- 用户画像页
- 首页
- 三个分析输入页
- 分析结果页
- 复盘任务页
- 历史记录页

### 5.2 前端第一阶段必须完成的能力

- 基于契约的 API 调用层
- 基于统一状态枚举的页面状态管理
- 401/403 跳转和会话失效处理
- 结果页主卡渲染
- 数据不足/失败/过期的状态展示

### 5.3 前端第一阶段禁止事项

- 禁止根据页面需要临时扩展后端返回字段
- 禁止把缺字段情况静默吞掉
- 禁止自己推断“这个状态大概等于成功”

## 6. 测试开工清单

### 6.1 第一阶段必须先建的测试集

- 认证与权限测试
- 分析任务主流程 smoke
- 失败态与降级态测试
- 结果页状态映射测试
- 复盘任务生成测试

### 6.2 测试样本必须覆盖

- 未登录访问
- token 失效
- 外部数据不足
- 分析超时
- 结果过期
- 高风险场景触发干预
- 复盘任务正常生成

## 7. 第一周交付清单

第一周不是“把功能做完”，而是把开工基础收稳。

### 后端

- 数据库迁移可跑通
- 认证方案定稿并有实现骨架
- API 错误响应统一
- `analysis_tasks` / `analysis_results` 核心模型落地

### 前端

- 页面壳体和路由可跑通
- API 客户端层建好
- 统一错误态和加载态组件建好
- 登录态守卫建好

### 测试

- 第一版 smoke 清单
- 第一版认证与异常用例
- 第一版联调数据样本

## 8. 第二周交付清单

### 后端

- 画像、股票搜索、分析任务创建接口可用
- 结果查询接口可返回基础结构
- 复盘任务自动生成链路打通

### 前端

- 画像页、输入页、结果页可联调
- `processing / ready / failed / expired` 状态可正确渲染

### 测试

- 主流程 smoke 跑第一轮
- 401/403、失败态、过期态开始验证

## 9. 联调前阻塞项

以下事项未完成前，不建议进入大范围联调：

- 认证逻辑仍带开发态放行
- API 返回结构未收口
- 任务状态枚举未统一
- 数据库迁移仍混有生产/开发数据
- 结果页错误态还没有明确口径

## 10. 内测前阻塞项

以下事项未完成前，不建议进入真实内测：

- 用户只能访问自己的数据还未验证
- 数据不足场景仍可能输出强结论
- 结果页过期态未完成
- 复盘任务无法稳定生成
- 日志无法按 `analysis_id` 追踪
- 关键告警还未建立

## 11. 模块级开工建议

### 11.1 认证模块

产出要求：

- 登录接口
- token 刷新接口
- 鉴权中间件
- 资源归属校验

### 11.2 分析任务模块

产出要求：

- `POST /api/v1/analysis`
- `GET /api/v1/analysis/:id`
- 任务状态更新机制
- 错误码和降级标记

### 11.3 结果结构模块

产出要求：

- `decision_card`
- `intervention`
- `review_task`
- `detail_panels`

必须服从：

- [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md)

### 11.4 复盘模块

产出要求：

- 自动创建复盘任务
- 查询待复盘任务
- 提交复盘结果

## 12. 每周研发例会建议

每周例会固定回答：

1. 本周改动是否破坏了基线文档
2. 哪个模块最堵联调
3. 哪个接口最不稳定
4. 哪类状态最容易误导用户
5. 下周优先消掉哪个阻塞项

## 13. 最终结论

这份开工清单的核心目的不是把任务列满，而是帮助团队用最小路径进入“稳定开发状态”。

当前最正确的推进方式不是同时把所有功能铺开，而是先把以下四条主线做实：

- 认证和权限
- 分析任务与结果结构
- 失败与降级状态
- 复盘任务闭环

只要这四条主线先站稳，后续联调、测试、内测都会顺很多。
