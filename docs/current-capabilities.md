# OverClocked Helpdesk — Current Capabilities Map

> 状态: OpenSpec 优化前的能力地图（pre-change capability assessment）
> 日期: 2026-06-10
> openspec 状态: 已初始化（`schema: spec-driven`），changes/archive/ 和 specs/ 均为空，尚无任何 OpenSpec change
> 后续计划: `quality-baseline`（planned, not started）— 为 mentor assignment 和 query creation 行为补测试
> 目的: 按角色记录已有能力、待验证行为、缺失的测试，以及在后续 change 中应被测试保护而非重写的关键行为

---

## 1. Team（团队）

### 1.1 已有能力

| # | 能力 | 端点/入口 | 代码位置 | 说明 |
|---|---|---|---|---|
| T1 | 提交工单 | `POST /submit` | `main.py:65-84` | 接收 team_id, issue, location；BackgroundTasks 调用 `notify_and_create_query()` 创建 PENDING Query + Slack 通知；返回 `{ok, team_id}` |
| T2 | 查看工单表单 | `GET /` | `main.py:57-62` | 渲染 `helpdesk_form.html`，40 个团队下拉、地点和问题输入，暗色 cyberpunk 主题 |
| T3 | 查看自己工单状态 | `GET /team-status?team=N` | `main.py:92-103` | 渲染 `team_status.html`，前端每 10 秒轮询 `GET /team/{team_id}/status` |
| T4 | 状态轮询 API | `GET /team/{team_id}/status` | `main.py:110-139` | 返回该 team 最新一条 Query 的 issue/status/mentor/updated_at；无 query 时返回 404 |
| T5 | QR 码预填 | `GET /?team=N` (query param) | `templates/helpdesk_form.html` | 通过 URL query param 预选团队，配合 QR 码扫码使用 |
| T6 | 暗/亮主题切换 | 前端 JS | `templates/helpdesk_form.html` | localStorage 持久化主题偏好 |

### 1.2 Planned `quality-baseline` 应保护的行为

> 以下行为属于现有生产路径，planned `quality-baseline` 的测试应锁定这些行为，后续 change 不应在无测试覆盖的情况下修改它们。

| # | 行为 | 所在代码 | 保护理由 |
|---|---|---|---|
| TP1 | `POST /submit` 接收表单 → `background_notify()` → `notify_and_create_query()` 创建 PENDING Query → 返回 `{ok, team_id}` | `main.py:65-84` → `services/notifier.py:6-33` | 工单创建的唯一入口，整个系统的主写路径 |
| TP2 | `notify_and_create_query()` 始终创建 status=PENDING, mentor_id=None 的 Query，Slack 通知独立于 DB commit | `services/notifier.py:13-31` | Query 的初始状态契约；Slack 失败不影响 query 创建的行为需被测试锁定 |
| TP3 | `GET /team/{team_id}/status` 查最新一条 Query（按 created_at DESC），无 query 时返回 404 | `main.py:110-139` | Team 端状态轮询的核心契约 |
| TP4 | Query 的 `team_id` 在 `POST /submit` 时由前端表单传入，服务端不校验 team 是否存在 | `main.py:65-84` | 现有行为（无论好坏）— 测试需先覆盖此路径，后续 change 才能安全地添加校验 |

### 1.3 待验证能力

| # | 描述 | 风险 |
|---|---|---|
| TV1 | `POST /submit` 不校验 team_id 是否存在 — SQLite 默认 `PRAGMA foreign_keys=OFF`，可能写入不存在的团队 | 数据完整性 |
| TV2 | 提交流程前端重定向到 `/team-status`，`success.html` (templates/success.html, 67行) 无任何路由渲染 | 死代码 |
| TV3 | QR 码生成的 `qrcode` 依赖不在 `requirements.txt` 中 | 启动崩溃风险 |

### 1.4 明显缺失的测试

- `POST /submit` → `notify_and_create_query()` 的端到端行为（Query 字段完整性、默认 status/menor_id）
- `GET /team/{team_id}/status` 无工单时的 404 行为
- Slack webhook 不可用时 Query 是否仍成功创建

---

## 2. Mentor（导师）

### 2.1 已有能力

| # | 能力 | 端点/入口 | 代码位置 | 说明 |
|---|---|---|---|---|
| M1 | 导师仪表盘 | `GET /mentors-dashboard` | `main.py:146-159` | 渲染 `mentor_dashboard.html`，bento-grid 布局，显示所有导师卡片、负载条 |
| M2 | 查看所有导师状态 | `GET /mentors/state` | `main.py:166-178` | 返回所有导师 id/name/is_active/current_load/max_load；前端每 5 秒轮询 |
| M3 | 切换在线状态 | `PATCH /mentors/{id}/toggle-availability` | `main.py:185-205` | 翻转 mentor.is_active，commit 后返回更新后状态 |
| M4 | 查看待处理工单 | `GET /queries/pending` | `api/queries.py:16-36` | 返回所有 status=PENDING 且 mentor_id=None 的工单 |
| M5 | 查看自己的工单 | `GET /queries/mentor/{id}` | `api/queries.py:42-74` | 返回 PENDING 未分配 + 已分配给自己的 ASSIGNED 工单 |
| M6 | 接受工单 | `PATCH /queries/{qid}/accept/{mid}` | `api/queries.py:80-244` | 分配 query → status=ASSIGNED → load+1 → 满载时 is_active=False → 发送 HTML 暗色邮件 |
| M7 | 解决工单 | `PATCH /queries/{qid}/resolve` | `api/queries.py:250-276` | status=RESOLVED → load-1（>0 守卫）→ 负载回落时 is_active=True；已 RESOLVED 幂等 |
| M8 | 查看单个工单 | `GET /queries/{qid}` | `api/queries.py:282-299` | 返回 query 全字段（含 isoformat created_at） |
| M9 | 接收分配通知邮件 | 内部（SMTP） | `api/queries.py:112-237` + `services/email_service.py` | HTML 暗色主题邮件，含 Team/Location/Issue 信息卡片 |

### 2.2 Planned `quality-baseline` 应保护的行为

> 以下行为是 mentor assignment 状态机的核心契约。Planned `quality-baseline` 的测试应锁定这些行为，防止后续 change 破坏状态机完整性。

| # | 行为 | 所在代码 | 保护理由 |
|---|---|---|---|
| MP1 | `accept_query` 成功路径：PENDING → ASSIGNED, mentor.current_load += 1, 返回 `{ok, query_id, mentor_id, current_load}` | `api/queries.py:101-109, 239-244` | Mentor Assignment 的核心成功路径 |
| MP2 | `accept_query` 满载关闭：current_load >= max_load 时自动设置 is_active = False | `api/queries.py:106-107` | 导师负载上限的自动保护机制 |
| MP3 | `accept_query` 拒绝已分配工单：status != PENDING 或 mentor_id 非空 → 400 "Query already taken" | `api/queries.py:95-96` | 防止重复分配的安全守卫 |
| MP4 | `accept_query` 拒绝非活跃导师：!mentor.is_active → 400 "Mentor not available" | `api/queries.py:98-99` | 防止下线导师被分配工单 |
| MP5 | `accept_query` 实体不存在：query 不存在 → 404, mentor 不存在 → 404 | `api/queries.py:89-93` | 标准 HTTP 语义 |
| MP6 | `resolve_query` 成功路径：status → RESOLVED, mentor.current_load -= 1（>0 守卫） | `api/queries.py:267-274` | 状态机回退路径的核心契约 |
| MP7 | `resolve_query` 负载恢复：current_load < max_load 时 is_active 恢复为 True | `api/queries.py:271-272` | 导师从满载恢复的自动机制 |
| MP8 | `resolve_query` 幂等：已 RESOLVED 的 query 再次 resolve → `{ok: true}`，不修改任何状态 | `api/queries.py:260-261` | 幂等性保证，防止重复操作破坏 mentor 状态 |
| MP9 | `resolve_query` 无 mentor 的 query：query.mentor_id=None 时仍可 RESOLVED，跳过 mentor 负载调整 | `api/queries.py:263-265, 269` | 边界场景 — query 在分配前被 resolve 的防御 |
| MP10 | `accept_query` 邮件在 DB commit **之后**发送，邮件失败不回滚 assignment | `api/queries.py:109, 232-237` | 当前通知与事务分离的设计决策（无论好坏需被测试锁定） |

### 2.3 待验证能力

| # | 描述 | 风险 |
|---|---|---|
| MV1 | `services/assigner.py` 定义了自动分配算法 `assign_mentor()`（primary → fallback least-loaded），但**未在任何路由或服务中调用**。当前系统采用导师手动自选模式 | 预留功能未接入，如果未来启用需验证算法正确性 |
| MV2 | `api/mentors.py` 整个 router (80行) 未被 `main.py` 注册。其中 `GET /mentors/{id}/queries` 引用了不存在的 `Query.is_resolved` 属性（模型使用 `status` 字段）。如果将来注册会触发运行时 AttributeError | 死代码 + 属性引用错误 |
| MV3 | `accept_query` 中 mentor.email 为空或 None 时仍调用 `send_email_alert()` | SMTP 连接失败/空收件人异常处理待验证 |
| MV4 | 两个 mentor 同时对同一 PENDING query 调用 accept — SQLite 默认隔离级别下的竞态行为待验证 | 并发安全 |
| MV5 | `PATCH /mentors/{id}/toggle-availability` 不校验当前负载：满载导师可被手动 toggle 为 active，随后可能被 accept 推送超载 | 状态不一致风险 |

### 2.4 明显缺失的测试

- `accept_query` 全线状态转换（成功 + 4 条拒绝分支 + 2 条 404 + 满载自动关闭）
- `resolve_query` 全线状态转换（成功 + 幂等 + 无 mentor + 负载恢复）
- `assign_mentor()` 算法逻辑（primary 可用 / primary 满载 / primary 非活跃 / 全满载返回 None / team 不存在返回 None）— 虽然未接入，但函数本身应被单元测试覆盖
- `toggle-availability` 与 accept 的交互（被 toggle 下线后仍可 accept 的时序问题）

---

## 3. Admin（管理员）

### 3.1 已有能力

| # | 能力 | 端点/入口 | 代码位置 | 说明 |
|---|---|---|---|---|
| A1 | 管理仪表盘 | `GET /admin` | `api/admin.py:27-46` | 渲染 `admin_dashboard.html`，显示 1-40 号团队卡片 + 所有 mentor 列表 |
| A2 | 生成团队 QR 码 | `POST /admin/teams/{id}/generate-qr` | `api/admin.py:52-58` | team_id ∈ [1, 40] 范围校验；调用 `generate_team_qr()` 写入 `static/qr/team_{id}.png` |
| A3 | 添加导师 | `POST /admin/mentors` | `api/admin.py:64-83` | 创建 Mentor(name, email, max_load)，默认 current_load=0, is_active=True |
| A4 | 编辑导师 | `PATCH /admin/mentors/{id}` | `api/admin.py:89-113` | 更新 name/email/max_load/is_active；若 current_load > 新 max_load 则 clamp 到新 max_load |
| A5 | 删除导师 | `DELETE /admin/mentors/{id}` | `api/admin.py:119-138` | current_load > 0 时拒绝 (400 "Cannot delete mentor with active workload") |
| A6 | QR 码存在性检查 | 内部 helper | `api/admin.py:20-21` | `qr_exists(team_id)` 检查 `static/qr/team_{id}.png` 是否在文件系统上存在 |

### 3.2 Planned `quality-baseline` 应保护的行为

| # | 行为 | 所在代码 | 保护理由 |
|---|---|---|---|
| AP1 | `generate_qr` 范围校验：team_id < 1 或 > 40 → 400 "Invalid team" | `api/admin.py:53-55` | Admin 写操作输入校验 |
| AP2 | `delete_mentor` 拒绝删除有活跃工单的 mentor：current_load > 0 → 400 | `api/admin.py:129-133` | 防止悬空工单的安全守卫 |
| AP3 | `delete_mentor` 正常删除：current_load = 0 → 200 `{ok: true}` | `api/admin.py:135-138` | Mentor 生命周期管理 |
| AP4 | `update_mentor` clamp 逻辑：current_load > 新 max_load → current_load 被 clamp 到新 max_load | `api/admin.py:109-110` | 防止负载超过上限的数据完整性保护 |
| AP5 | `add_mentor` 默认值：current_load 必为 0, is_active 必为 True | `api/admin.py:73-76` | 新 mentor 的初始状态契约 |

### 3.3 待验证能力

| # | 描述 | 风险 |
|---|---|---|
| AV1 | `POST /admin/mentors` 和 `PATCH /admin/mentors/{id}` 不校验 name/email 空串或重复 | 垃圾数据入库 |
| AV2 | `DELETE /admin/mentors/{id}` 删除 mentor 后，关联 team 的 `mentor_id` FK 变为悬空引用（SQLite 无 FK enforce） | 数据完整性 |
| AV3 | `generate_qr` 依赖 `static/qr/` 目录，由 `utils/qr.py` 在 import 时创建。若 qr 模块未被 import，`StaticFiles` 挂载 `static/` 可能因目录缺失报错 | 启动顺序依赖 |

### 3.4 明显缺失的测试

- `generate_qr` 范围边界（0, 1, 40, 41）
- `delete_mentor` 三条分支（不存在 / 有活跃工单 / 正常删除）
- `update_mentor` clamp 边界值（current_load = 新 max_load / current_load > 新 max_load / current_load < 新 max_load）
- `add_mentor` 创建后 current_load/is_active 默认值

---

## 4. 跨角色基础设施

### 4.1 已有能力

| # | 能力 | 说明 |
|---|---|---|
| I1 | SQLite 数据库 | SQLAlchemy ORM，`helpdesk.db`，启动时 `Base.metadata.create_all(bind=engine)` 自动建表 |
| I2 | FastAPI 路由器 | 3 个已注册 router（queries, qr, admin）+ main.py 内联端点 |
| I3 | Slack Webhook 通知 | `services/slack_service.py` — POST JSON 到 `SLACK_WEBHOOK_URL` |
| I4 | SMTP 邮件通知 | `services/email_service.py` — SMTP_SSL，支持 text + HTML |
| I5 | QR 码生成 | `utils/qr.py` — `qrcode` 库生成 PNG 到 `static/qr/` |
| I6 | Jinja2 模板 | 5 个模板，统一暗色 cyberpunk 主题 |
| I7 | 种子数据 | `scripts/seed_data.py` — 3 个 Mentor + 3 个 Team |

### 4.2 Planned `quality-baseline` 应保护的行为

| # | 行为 | 所在代码 | 保护理由 |
|---|---|---|---|
| IP1 | `background_notify()` 每次创建独立 `SessionLocal()`，finally 中 close — 不经过 FastAPI DI | `main.py:40-50` | 后台任务的会话生命周期模式，与其他端点不同 |
| IP2 | `get_db()` generator yield Session，FastAPI 依赖注入自动 close | `db/session.py` (get_db) | 标准 FastAPI 数据库依赖模式 |
| IP3 | 启动时 `Base.metadata.create_all(bind=engine)` 自动建表，无 migration 框架 | `main.py:31` | 数据库初始化方式，任何模型变更需考虑此行为 |
| IP4 | `send_slack_alert()` 在 `SLACK_WEBHOOK_URL` 为空/None 时 `requests.post(None, ...)` | `services/slack_service.py:15` | 通知失败模式，需测试覆盖当前异常行为 |

### 4.3 跨角色已知风险

1. **无鉴权** — 所有端点公开访问，admin/mentor 操作无任何登录或权限校验
2. **FK 不强制** — SQLite `PRAGMA foreign_keys=OFF`，`POST /submit` 可写入不存在的 team_id
3. **无 migration 工具** — 无 Alembic，模型变更靠 `create_all()` 自动同步
4. **无分页** — `GET /queries/pending` 和 `GET /mentors-dashboard` 无条件返回全表
5. **通知失败无回滚** — Slack 失败不影响工单创建；邮件在 commit 之后发送，失败不回滚 assignment
6. **`qrcode` 不在 `requirements.txt`** — 隐式依赖
7. **`api/mentors.py` 为未注册死代码** — 含 `Query.is_resolved` 属性引用错误
8. **硬编码邮箱** — `scripts/test_email.py` 含真实 Gmail 地址
9. **重复路由潜伏** — `main.py` 和 `api/mentors.py` 定义相同路由 (`GET /mentors/state`, `PATCH /mentors/{id}/toggle-availability`)，后者未注册所以当前无害，注册即冲突

### 4.4 基础设施层面缺失的测试

- `get_db()` 会话生命周期（yield → close 的正确性）
- `background_notify()` 手动 SessionLocal 的隔离和清理
- Slack webhook URL 为空/None 时的异常路径
- SMTP 凭据未配置时的优雅降级行为

---

## 5. 死代码清单（pre-change 状态快照）

| 位置 | 内容 | 行数 | 现状 |
|---|---|---|---|
| `api/mentors.py` | 完整 router（toggle, state, queries） | 80 | **未注册**；含 `Query.is_resolved` 属性引用错误（模型使用 `status`） |
| `services/assigner.py` | `assign_mentor()` 自动分配函数 | 34 | **未被任何路由或服务调用**；定义清晰但未接入 |
| `templates/success.html` | 工单提交成功页 | 67 | **无路由渲染**；当前提交流程重定向到 `/team-status` |

---

## 6. Planned `quality-baseline` 覆盖汇总

> 以下全部为 **planned / pre-change context**。尚未创建 OpenSpec change，未开始任何实现。

### 测试目标分级

| 优先级 | 测试目标 | 覆盖类别 | 关键行为数 | 来源章节 |
|---|---|---|---|---|
| 高 | `accept_query` (api/queries.py:80-244) | Mentor Assignment | 10 项 (MP1-MP10) | 2.2 |
| 高 | `notify_and_create_query` (services/notifier.py:6-33) | Query Creation | 2 项 (TP1-TP2) | 1.2 |
| 中 | `resolve_query` (api/queries.py:250-276) | 状态机回退 / 回归风险 | 4 项 (MP6-MP9) | 2.2 |
| 中 | `delete_mentor` (api/admin.py:119-138) | Admin 安全守卫 | 2 项 (AP2-AP3) | 3.2 |
| 低 | `assign_mentor` (services/assigner.py) | 预留算法验证 | 5 条分支 | 2.4 |
| 低 | `update_mentor` clamp / `add_mentor` 默认值 / `generate_qr` 范围 | Admin CRUD 边界 | 3 项 (AP1, AP4-AP5) | 3.2 |

### 不应在测试覆盖前重写的已有行为

以下行为如果被修改，测试必须先行覆盖：

1. Query 创建时的初始状态契约 (status=PENDING, mentor_id=None)
2. accept_query 的全部拒绝分支（4 条 400）和 404 分支（2 条）
3. Mentor load 的增减逻辑和 is_active 自动切换
4. resolve_query 的幂等性保证
5. 通知与事务的分离模式（Slack/邮件在 commit 后发送，失败不回滚）
6. delete_mentor 的 current_load 守卫
7. update_mentor 的 current_load clamp
