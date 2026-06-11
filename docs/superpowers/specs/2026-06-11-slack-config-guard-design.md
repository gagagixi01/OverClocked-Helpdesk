# Slack Config Guard — Test Strategy & Bugfix Design

> 日期: 2026-06-11
> OpenSpec change: `stabilize-slack-notification-config`
> 设计基于: `openspec/changes/stabilize-slack-notification-config/proposal.md`, `design.md`, `specs/slack-config-guard/spec.md`

---

## 1. 问题

`slack_service.py:send_slack_alert()` 无条件调用 `requests.post(settings.SLACK_WEBHOOK_URL, ...)`。`SLACK_WEBHOOK_URL` 默认值为 `None`（`config.py:10`）。未配置 webhook 的部署环境中，`requests.post(None, ...)` 会抛出 `requests.exceptions.MissingSchema`。

quality-baseline 测试（`test_query_creation.py`）通过 monkeypatch 覆盖了 `notifier.send_slack_alert`，该问题在测试中不可见。

## 2. Bugfix

一行 guard，放在 `send_slack_alert` 函数体最顶部：

```python
# slack_service.py — before
def send_slack_alert(team_name: str, location: str, issue: str) -> bool:
    payload = {
        "text": (
            "*New Helpdesk Query*\n"
            f"*Team:* {team_name}\n"
            f"*Location:* {location}\n"
            f"*Issue:* {issue}"
        )
    }

    response = requests.post(
        settings.SLACK_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

    return response.status_code == 200
```

```python
# slack_service.py — after
def send_slack_alert(team_name: str, location: str, issue: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False

    payload = {
        "text": (
            "*New Helpdesk Query*\n"
            f"*Team:* {team_name}\n"
            f"*Location:* {location}\n"
            f"*Issue:* {issue}"
        )
    }

    response = requests.post(
        settings.SLACK_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

    return response.status_code == 200
```

**设计要点：**

- `if not` 同时覆盖 `None` 和 `""`，与 `config.py:10` 的 `str | None = None` 类型匹配
- guard 在 payload 构建之前 — URL 缺失时不浪费构造 Slack 格式文本
- 不引入 logging、不抛异常、不修改返回值语义 — `False` 统一表示"通知未发送"
- `notifier.py:27-29` 已忽略 `send_slack_alert` 返回值，`False` 不改变调用方行为

## 3. 测试架构

```
tests/
  conftest.py                   # 现有 fixtures（不变）
  test_query_creation.py        # notifier 层测试（不变）
  test_mentor_assignment.py     # mentor assignment 测试（不变）
  test_slack_service.py         # ✨ 新增 — send_slack_alert 单元测试
```

**两层互补：**

| 测试文件 | 测试目标 | Mock 方式 |
|---|---|---|
| `test_query_creation.py` | notifier 编排逻辑 | monkeypatch `notifier.send_slack_alert` |
| `test_slack_service.py` | slack_service 配置 guard | monkeypatch `settings.SLACK_WEBHOOK_URL` + mock `requests.post` |

`test_slack_service.py` 不依赖数据库 — `send_slack_alert` 只做 HTTP 调用，不需要 DB session 或 TestClient。

**Mock 决策：monkeypatch settings 属性**

`send_slack_alert` 直接从模块级 `from overclocked_helpdesk.config import settings` 读取配置，不通过依赖注入。使用 `monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", value)` 控制配置值，配合 `mocker.patch("overclocked_helpdesk.services.slack_service.requests.post")` 验证是否调用。与现有 `conftest.py` 中的 monkeypatch 模式一致。

替代方案（环境变量注入）被拒绝：需要处理清理逻辑，且与现有测试模式不一致。

## 4. 测试用例

### 4.1 URL 为 None → 返回 False，不调用 requests.post

```python
def test_returns_false_when_webhook_url_is_none(self, monkeypatch):
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", None)
    mock_post = mocker.patch(
        "overclocked_helpdesk.services.slack_service.requests.post"
    )

    result = send_slack_alert("Team A", "Room 1", "No WiFi")

    assert result is False
    mock_post.assert_not_called()
```

验收标准：
- 缺失 webhook 时不会调用 `requests.post`（`assert_not_called`）
- `send_slack_alert` 返回 `False`

### 4.2 URL 为空字符串 → 同 None

```python
def test_returns_false_when_webhook_url_is_empty_string(self, monkeypatch):
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "")
    mock_post = mocker.patch(
        "overclocked_helpdesk.services.slack_service.requests.post"
    )

    result = send_slack_alert("Team B", "Room 2", "Printer broken")

    assert result is False
    mock_post.assert_not_called()
```

与 Case 1 结构一致，区别仅在 `""` vs `None`。验证 `if not settings.SLACK_WEBHOOK_URL` 同时覆盖两者。

### 4.3 URL 存在 → 原有 payload 形状不变

```python
def test_calls_requests_post_with_correct_payload_when_url_present(
    self, monkeypatch
):
    monkeypatch.setattr(
        settings, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"
    )
    mock_post = mocker.patch(
        "overclocked_helpdesk.services.slack_service.requests.post"
    )
    mock_post.return_value.status_code = 200

    result = send_slack_alert("Team C", "Room 3", "Monitor broken")

    assert result is True
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://hooks.slack.com/test"
    assert call_args[1]["json"]["text"] is not None
    assert "Team C" in call_args[1]["json"]["text"]
    assert "Room 3" in call_args[1]["json"]["text"]
    assert "Monitor broken" in call_args[1]["json"]["text"]
    assert call_args[1]["timeout"] == 10
```

验收标准：
- `requests.post` 被调用一次，URL 正确，timeout=10
- payload 的 `text` 字段包含三个参数值（验证数据传递，不验证精确格式化字符串）

### 4.4 不测什么

- **其他 HTTP 状态码** — `response.status_code == 200` 是已有逻辑，不属于 guard 范围
- **网络异常** — guard 只负责配置缺失路径，网络失败由 requests 层处理

### 4.5 回归检查

运行现有 `tests/test_query_creation.py` — QC1、QC2、QC3 全部通过。这些测试 monkeypatch `notifier.send_slack_alert`，完全绕过 `slack_service.py`，因此 guard 修改对它们零影响。

## 5. 实施顺序

1. 创建 `tests/test_slack_service.py` — 3 个测试用例（此时全部 FAIL — 验证测试有效）
2. 修改 `slack_service.py` 添加 guard 行
3. 运行新测试 — 全部 PASS
4. 运行 `test_query_creation.py` — QC1-QC3 通过
5. 运行全量测试确认无回归
