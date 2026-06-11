## Context

`slack_service.py` 的 `send_slack_alert()` 当前无条件调用 `requests.post(settings.SLACK_WEBHOOK_URL, ...)`。`SLACK_WEBHOOK_URL` 在 `config.py` 中定义为 `str | None = None`，默认值为 `None`。未配置 webhook 的部署环境中，`requests.post(None, ...)` 会抛出 `requests.exceptions.MissingSchema` 或类似异常。

quality-baseline 测试通过 monkeypatch 覆盖了 `notifier` 模块中的 `send_slack_alert` 引用，因此该问题在测试中不可见。需要在 `slack_service.py` 层面添加防御性检查。

## Goals / Non-Goals

**Goals:**
- `SLACK_WEBHOOK_URL` 为 `None` 或空字符串时，`send_slack_alert()` 不调用 `requests.post`，返回 `False`
- 有合法 webhook URL 时，行为与当前完全一致（payload 结构、超时、返回值）
- 新增针对 `slack_service.py` 的单元测试，直接验证配置边界

**Non-Goals:**
- 不接入真实 Slack API
- 不引入重试队列或异步通知
- 不修改 `notifier.py` 或 `config.py`
- 不添加日志记录（保持最小改动）

## Decisions

**Decision 1: 在函数入口添加 early-return guard**

在 `send_slack_alert()` 函数体的最前面，添加对 `settings.SLACK_WEBHOOK_URL` 的检查：

```python
if not settings.SLACK_WEBHOOK_URL:
    return False
```

`not` 同时覆盖 `None` 和空字符串 `""`，语义明确。

替代方案：使用 `if settings.SLACK_WEBHOOK_URL is None or settings.SLACK_WEBHOOK_URL == ""`。更显式但更冗长，无实际收益。

**Decision 2: 测试使用 `monkeypatch` 控制 settings 而非 mock requests**

通过 `monkeypatch.setattr` 修改 `settings.SLACK_WEBHOOK_URL` 的值，配合 `mocker.patch("requests.post")` 验证 `requests.post` 是否被调用。这种方法直接测试 `slack_service.py` 的真实逻辑路径，不需要 mock 函数本身。

**Decision 3: 测试文件位置和命名**

新建 `tests/test_slack_service.py`，与现有 `tests/test_query_creation.py` 并列。测试直接 import `send_slack_alert`，不通过 notifier 间接调用。

## Risks / Trade-offs

- **配置检查位置**: 只在 `send_slack_alert` 入口检查，不修改 `config.py` 或全局设置。如果未来其他模块也直接使用 `SLACK_WEBHOOK_URL`，需各自检查。
- **静默失败**: 返回 `False` 而非抛异常，意味着调用方（`notifier.py`）无法区分"未配置"和"HTTP 请求失败"。当前 notifier 已忽略返回值，因此无实际影响。
