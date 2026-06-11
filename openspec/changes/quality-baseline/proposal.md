## Why

当前 OverClocked Helpdesk 项目的 mentor assignment 和 query creation 两条核心写路径完全没有自动化测试覆盖。对这两条路径的任何后续修改（重构、接入 `assign_mentor()` 自动分配、添加输入校验、替换通知后端等）都会在没有安全网的情况下进行。本 change 建立质量基线，用测试锁定当前行为，使后续 change 可以在有回归保护的前提下进行。

## What Changes

- 新增 `mentor-assignment-tests` 测试套件，覆盖 `accept_query` 和 `resolve_query` 的状态机全部分支（成功路径 + 4 条拒绝守卫 + 2 条 404 + 满载自动去激活/恢复 + 幂等性 + 邮件发送行为）
- 新增 `query-creation-tests` 测试套件，覆盖 `notify_and_create_query()` 的最小成功路径和 Slack 通知分离行为
- 如有必要，新增最低限度的测试夹具代码（如 DB session 工具、mock 工厂），但不在本 change 中重写服务层、路由层或模板
- 不改变用户可见功能。当前行为如有缺陷，用测试和文档暴露，不扩大为完整重构

## Capabilities

### New Capabilities

- `mentor-assignment-tests`: 覆盖 `PATCH /queries/{id}/accept/{mid}` 和 `PATCH /queries/{id}/resolve` 的全部状态转换分支。保护的行为定义在 `docs/current-capabilities.md` 第 2.2 节 MP1-MP10，包括正常分配、满载关闭、拒绝已分配工单、拒绝非活跃导师、实体不存在、resolve 负载恢复、幂等性、无 mentor 的 query resolve，以及邮件在 commit 之后发送的设计决策。
- `query-creation-tests`: 覆盖 `notify_and_create_query()` 的最小成功路径。保护的行为定义在 `docs/current-capabilities.md` 第 1.2 节 TP1-TP2，包括 Query 初始状态契约（status=PENDING, mentor_id=None）和 Slack 通知独立于 DB commit 的行为。

### Modified Capabilities

_（无现有 spec 需要修改；openspec/specs/ 为空）_

## Impact

- 受保护代码: `overclocked_helpdesk/api/queries.py`（accept_query, resolve_query），`overclocked_helpdesk/services/notifier.py`（notify_and_create_query），`overclocked_helpdesk/main.py`（background_notify）
- 新增文件: 测试文件（路径由 tasks.md 确定），无业务代码修改
- 新增依赖: 测试运行器（如 pytest）如尚未安装则加入 requirements.txt
- 不触及: `overclocked_helpdesk/api/admin.py`、`overclocked_helpdesk/services/assigner.py`、`overclocked_helpdesk/services/email_service.py`、`overclocked_helpdesk/services/slack_service.py`、`templates/`、`scripts/`
