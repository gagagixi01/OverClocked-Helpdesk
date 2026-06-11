## ADDED Requirements

本 spec 覆盖的行为边界定义在 `docs/current-capabilities.md` 第 1.2 节 TP1-TP2。测试 SHALL NOT 修改业务代码，仅记录当前实际行为。

### Requirement: Create a query with PENDING status and no mentor

系统 SHALL 通过 `notify_and_create_query()` 创建一条 status="PENDING" 且 mentor_id=None 的 Query 记录，并调用 Slack webhook 通知。Slack 通知 SHALL 在 DB commit 之后执行，其失败 SHALL NOT 影响 Query 的持久化。

保护的行为: `docs/current-capabilities.md` TP1, TP2

#### Scenario: Successful query creation
- **WHEN** 调用 `notify_and_create_query(db, team_id, issue, location)` 且 Slack webhook 可用
- **THEN** 数据库中创建一条 Query，其 status="PENDING"，mentor_id=None，team_id/issue/location 与传入参数一致，created_at 不为空，且调用 `send_slack_alert()` 发送通知

#### Scenario: Query created even when Slack is unavailable
- **WHEN** `send_slack_alert()` 返回 False（模拟 Slack webhook 不可用）
- **THEN** Query 记录仍成功持久化到数据库，status="PENDING"，mentor_id=None

#### Scenario: Query fields match input exactly
- **WHEN** 调用 `notify_and_create_query(db, team_id=5, issue="Network down", location="Room 301")`
- **THEN** 创建出的 Query 的 team_id=5，issue="Network down"，location="Room 301"
