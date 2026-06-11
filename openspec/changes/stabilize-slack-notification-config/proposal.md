## Why

`slack_service.py` 在 `SLACK_WEBHOOK_URL` 为 `None` 或空字符串时直接调用 `requests.post(None, ...)`，可能抛出异常。当前 quality-baseline 测试通过 monkeypatch 绕过了这个问题，但生产环境中未配置 Slack webhook 时会导致运行时错误。需要让 `send_slack_alert` 优雅降级，而不是崩溃。

## What Changes

- `send_slack_alert()` 在 `SLACK_WEBHOOK_URL` 缺失或为空时，不调用 `requests.post`，直接返回 `False`
- 新增 `slack_service` 单元测试，验证缺失 webhook 时不调用 `requests.post` 且返回 `False`
- 原有 payload 结构和成功路径行为保持不变
- 不接入真实 Slack，不引入重试队列，不修改 notifier 架构

## Capabilities

### New Capabilities

- `slack-config-guard`: `send_slack_alert()` 在 `SLACK_WEBHOOK_URL` 缺失或为空时返回 `False`，不调用外部 HTTP 服务

### Modified Capabilities

<!-- None — existing caps keep same requirements -->

## Impact

- `overclocked_helpdesk/services/slack_service.py` — 添加 webhook URL 存在性检查
- `tests/` — 新增 `test_slack_service.py`，验证两种边界：URL 缺失和 URL 存在时 payload 不变
- 现有 `test_query_creation.py` 测试不受影响（通过 monkeypatch 绕过 slack_service 实现）
