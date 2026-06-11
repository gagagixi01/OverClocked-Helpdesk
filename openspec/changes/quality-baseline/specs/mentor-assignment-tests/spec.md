## ADDED Requirements

本 spec 覆盖的行为边界定义在 `docs/current-capabilities.md` 第 2.2 节 MP1-MP10。测试 SHALL NOT 修改业务代码，仅记录当前实际行为。

### Requirement: Mentor accepts a pending query

系统 SHALL 允许活跃 mentor 接受一条 status=PENDING 且 mentor_id=None 的 query，接受后 query 状态变为 ASSIGNED，mentor 负载增加，且系统返回成功响应。

保护的行为: `docs/current-capabilities.md` MP1, MP2

#### Scenario: Successful acceptance
- **WHEN** 存在一条 status=PENDING 且 mentor_id=None 的 query，mentor 状态为 is_active=True 且 current_load < max_load
- **THEN** query.status 变为 "ASSIGNED"，query.mentor_id 等于该 mentor.id，mentor.current_load 增加 1，返回 `{"ok": true, "query_id": <id>, "mentor_id": <id>, "current_load": <new_load>}`

#### Scenario: Mentor becomes inactive when reaching max load
- **WHEN** mentor.current_load + 1 >= mentor.max_load 时接受新 query
- **THEN** mentor.is_active 变为 False

#### Scenario: Mentor stays active below max load
- **WHEN** mentor.current_load + 1 < mentor.max_load 时接受新 query
- **THEN** mentor.is_active 保持 True

### Requirement: Reject acceptance of already-assigned query

系统 SHALL 拒绝 mentor 接受一条已经被分配或状态不是 PENDING 的 query。

保护的行为: `docs/current-capabilities.md` MP3

#### Scenario: Query already has a mentor
- **WHEN** query.mentor_id 不为 None 或 query.status 不为 "PENDING"
- **THEN** 返回 HTTP 400 "Query already taken"，query 和 mentor 状态均不变

### Requirement: Reject acceptance by inactive mentor

系统 SHALL 拒绝 is_active=False 的 mentor 接受任何 query。

保护的行为: `docs/current-capabilities.md` MP4

#### Scenario: Inactive mentor tries to accept
- **WHEN** mentor.is_active 为 False
- **THEN** 返回 HTTP 400 "Mentor not available"，query 状态不变

### Requirement: Return 404 for non-existent entities in accept

系统 SHALL 对不存在的 query 或 mentor 返回 404。

保护的行为: `docs/current-capabilities.md` MP5

#### Scenario: Query not found during accept
- **WHEN** query_id 对应的 Query 不存在
- **THEN** 返回 HTTP 404 "Query not found"

#### Scenario: Mentor not found during accept
- **WHEN** mentor_id 对应的 Mentor 不存在
- **THEN** 返回 HTTP 404 "Mentor not found"

### Requirement: Resolve a query and decrement mentor load

系统 SHALL 将 query 标记为 RESOLVED，并递减关联 mentor 的负载（如有）。已 RESOLVED 的 query 重复 resolve SHALL 幂等返回。

保护的行为: `docs/current-capabilities.md` MP6, MP7, MP8, MP9

#### Scenario: Successful resolve with mentor
- **WHEN** 存在一条 status 为 ASSIGNED 且 mentor_id 不为 None 的 query
- **THEN** query.status 变为 "RESOLVED"，mentor.current_load 减少 1，返回 `{"ok": true, "query_id": <id>}`

#### Scenario: Mentor reactivates after resolve below max load
- **WHEN** mentor 因满载 (current_load >= max_load) 而 is_active=False，resolve 后 current_load < max_load
- **THEN** mentor.is_active 恢复为 True

#### Scenario: Resolve without mentor on query
- **WHEN** query.mentor_id 为 None（PENDING 状态下直接 resolve）
- **THEN** query.status 变为 "RESOLVED"，不操作任何 mentor 的 current_load，返回 `{"ok": true, "query_id": <id>}`

#### Scenario: Idempotent resolve of already-resolved query
- **WHEN** query.status 已为 "RESOLVED"
- **THEN** 返回 `{"ok": true}`，不修改 query 和 mentor 的任何状态

#### Scenario: Current load never goes negative
- **WHEN** resolve 操作使 mentor.current_load 递减
- **THEN** mentor.current_load 不会小于 0（即前值 > 0 时才递减）

### Requirement: Return 404 for non-existent query in resolve

系统 SHALL 对不存在的 query_id 在 resolve 操作中返回 404。

保护的行为: 代码依据 `api/queries.py:257-258`（resolve_query 第一行判断 `if not query: raise HTTPException(404)`）

#### Scenario: Query not found during resolve
- **WHEN** query_id 对应的 Query 不存在
- **THEN** 返回 HTTP 404 "Query not found"

### Requirement: Email notification on accept is sent after commit

系统 SHALL 在 DB commit 完成后才发送邮件通知，邮件发送失败 SHALL NOT 回滚 query 的 assignment。

保护的行为: `docs/current-capabilities.md` MP10

#### Scenario: Email sent after successful commit
- **WHEN** accept_query 成功 commit query 和 mentor 状态变更
- **THEN** 系统调用 `send_email_alert()` 发送确认邮件

#### Scenario: Email failure does not rollback assignment
- **WHEN** `send_email_alert()` 返回 False（发送失败）
- **THEN** query 已分配给 mentor 的状态不会被回滚或撤销
