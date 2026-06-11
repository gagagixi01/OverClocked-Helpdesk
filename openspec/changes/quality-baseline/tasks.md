## 1. 测试基础设施搭建

- [ ] 1.1 确认 `pytest` 和 `httpx` 是否已在当前 venv 中可用，若缺失则添加到 `requirements.txt` 并安装
- [ ] 1.2 创建 `tests/` 目录和 `tests/conftest.py`，提供共享 fixtures：SQLite 内存 engine/session factory、FastAPI TestClient、seed helper（创建 mentor + team + query）
- [ ] 1.3 创建 Slack webhook 和 SMTP email 的 mock fixtures（默认返回 True 模拟成功；如需测试失败路径则提供可选参数化）

## 2. Query Creation 测试

- [ ] 2.1 实现 `tests/test_query_creation.py`，覆盖 `notify_and_create_query()` 的最小成功路径：Query 创建后 status=PENDING, mentor_id=None, 字段完整 (spec: query-creation-tests / Requirement 1 / Scenario: Successful query creation)
- [ ] 2.2 实现 Slack 不可用时 Query 仍成功创建的测试 (spec: query-creation-tests / Requirement 1 / Scenario: Query created even when Slack is unavailable)
- [ ] 2.3 实现字段精确传递的测试 (spec: query-creation-tests / Requirement 1 / Scenario: Query fields match input exactly)
- [ ] 2.4 运行 `pytest tests/test_query_creation.py -v` 确认全部通过

## 3. Mentor Assignment 测试 — accept_query

- [ ] 3.1 实现正常接受测试：PENDING → ASSIGNED，mentor.current_load +1 (spec: mentor-assignment-tests / Requirement 1 / Scenario: Successful acceptance)
- [ ] 3.2 实现满载自动去激活测试：current_load +1 >= max_load → is_active=False (spec: mentor-assignment-tests / Requirement 1 / Scenario: Mentor becomes inactive when reaching max load)
- [ ] 3.3 实现未满载保持活跃测试：current_load +1 < max_load → is_active 不变 (spec: mentor-assignment-tests / Requirement 1 / Scenario: Mentor stays active below max load)
- [ ] 3.4 实现拒绝已分配工单测试：status != PENDING 或 mentor_id 非空 → 400 (spec: mentor-assignment-tests / Requirement 2 / Scenario: Query already has a mentor)
- [ ] 3.5 实现拒绝非活跃导师测试：!mentor.is_active → 400 (spec: mentor-assignment-tests / Requirement 3 / Scenario: Inactive mentor tries to accept)
- [ ] 3.6 实现实体不存在测试：query 不存在 → 404，mentor 不存在 → 404 (spec: mentor-assignment-tests / Requirement 4 / Scenario: Query not found / Mentor not found)
- [ ] 3.7 实现邮件在 commit 后发送、失败不回滚的测试 (spec: mentor-assignment-tests / Requirement: Email notification on accept is sent after commit / Scenario: Email sent after successful commit / Email failure does not rollback assignment)

## 4. Mentor Assignment 测试 — resolve_query

- [ ] 4.1 实现正常 resolve 测试：ASSIGNED → RESOLVED，mentor.current_load -1 (spec: mentor-assignment-tests / Requirement 5 / Scenario: Successful resolve with mentor)
- [ ] 4.2 实现负载恢复测试：current_load 从 max_load 下降后 is_active 恢复为 True (spec: mentor-assignment-tests / Requirement 5 / Scenario: Mentor reactivates after resolve below max load)
- [ ] 4.3 实现无 mentor 的 query resolve 测试 (spec: mentor-assignment-tests / Requirement 5 / Scenario: Resolve without mentor on query)
- [ ] 4.4 实现重复 resolve 幂等测试：已 RESOLVED 再次 resolve → `{ok: true}`，状态不变 (spec: mentor-assignment-tests / Requirement 5 / Scenario: Idempotent resolve)
- [ ] 4.5 实现 current_load 不下穿 0 的测试 (spec: mentor-assignment-tests / Requirement 5 / Scenario: Current load never goes negative)
- [ ] 4.6 实现 resolve 时 query 不存在的测试 (spec: mentor-assignment-tests / Requirement: Return 404 for non-existent query in resolve / Scenario: Query not found during resolve)
- [ ] 4.7 运行 `pytest tests/test_mentor_assignment.py -v` 确认全部通过

## 5. 最终验证

- [ ] 5.1 运行完整测试套件 `pytest tests/ -v`，确认零失败
- [ ] 5.2 检查测试输出确认每个 spec scenario 至少有一条对应测试
