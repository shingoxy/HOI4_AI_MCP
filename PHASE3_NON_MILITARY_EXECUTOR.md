# Phase 3 — Non-Military GUI Executor

更新日期：2026-10-02。状态：**COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 PoC）**。

本轮完成剩余 Production、Construction、Laws、Advisors、Trade。没有新增 Phase 子编号，没有进入 Army / Front / Air / Navy / Strategy Planner / Full AI Player。Research、Focus、factory assignment 的既有实机证据保留在 [Phase 3A](PHASE3A_GUI_EXECUTOR.md) 和 [Phase 3B-1](PHASE3B1_PRODUCTION_EXECUTOR.md)，本轮没有重演；Phase 1 / 2 没有重新调查或修改 Telemetry Mod。

## 支持的语义接口

| API | 已校准范围 / 确认方式 |
| --- | --- |
| `select_research(slot, tech_id)` / `select_focus(focus_id)` | 历史三项跟踪科技及莱茵兰，既有 GUI + telemetry 确认 |
| `get_production_lines()` | `--non-military` 完整紧凑军工列表，最多十条；全列表身份/顺序/数量 |
| `set_production_factory_count(line_id, factories)` | 保留原校准 0–15 数字 AND factory grid 路径；未重做 live |
| `create_production_line(equipment_id)` | `infantry_equipment_1`、`support_equipment_1`；仅增加一条的完整 diff |
| `delete_production_line(line_id)` | 重新验证临时身份、已知确认框、仅移除目标 |
| `reorder_production_line(line_id, direction)` | `up` / `down` 一步；精确全列表顺序 diff |
| `get_construction()` | 最多八个完整可见已知队列项；顺序、州、类型、数量、临时身份 |
| `build(state_id, building_type, count=1)` | 州 64 Brandenburg、65 Sachsen、66 Niederschlesien；`civilian_factory` / `military_factory` / `infrastructure`；单次一栋 |
| `cancel_construction(queue_item_id)` | 州名/建筑/确认框身份验证；仅目标消失 |
| `change_construction_priority(queue_item_id, direction)` | `up` / `down` 一步，精确顺序对照 |
| `change_economy_law(law_id)` | `low_economic_mobilisation` / `partial_economic_mobilisation`；PP、支持度、可选状态、确认框及重复 readback |
| `change_conscription_law(law_id)` | `volunteer_only` / `limited_conscription`；同上 |
| `get_advisors()` / `hire_advisor(advisor_id)` | 德国三顾问槽，只识别空槽和 `advisor_schacht`；实际名称/肖像/可选状态/75 PP，槽位结果重复确认 |
| `get_trade_state()` / `set_trade_import(resource, country, civilian_factories)` | `steel` / `SWE` / 0、1、2；实际合同数量、民工数量与 delivered/requested 联合确认，再重开合同重复读数 |

装备 catalog 分离 semantic ID、GUI display identity、supported state 和 identity source；未独立证实的内部 equipment ID 为 `null`，不由中文名猜测。三个州 ID 用安装游戏州定义及 GUI 州名/GER 所有权核对。沙赫特 `GER_hjalmar_schacht` 已核对安装游戏角色定义；顾问槽仍是 GUI 临时对象。

Construction 不合并相同州/建筑的重复队列；遇到已有同类项拒绝新增。建筑进度为 UNKNOWN；民工分配仅识别已校准 0 / 3 / 15，其他读数为 `null`。Trade getter 只返回已校准 SWE 钢铁合同，不代表全资源/全国家贸易总览。

未支持：换生产装备、截断的炮兵 picker、滚动生产列表、任意州/任意相机、批量建筑、无法识别的队列、贸易法、其他顾问/资源/国家/进口数量、任意分辨率。未知 GUI 内容拒绝动作，不硬凑成功。

## 架构与复用

调用链：Agent → adapter boundary → Observation / Action / Result → MCP 或 Python API → Domain Service → deterministic GUI Executor → InputBackend → 正常 HOI4 GUI → readback。本轮提供契约边界，没有实现完整 Agent Adapter。

`OperatorAPI.execute(action, arguments)` 用方法签名验证语义参数。Agent 不传坐标、模板、窗口、PID、Computer Use 对象。官方 MCP SDK stdio 验证服务 v0.6.0 的 **25 tools**；GUI runtime 由操作者在服务端显式附加，默认不连接 GUI。现有聊天七查询注册未改，新 action 在当前 chat 的发现/调用仍 UNKNOWN。

| 新模块 | 职责 |
| --- | --- |
| `src/hoi4_operator/contracts.py`、`operator.py` | 六种 ActionStatus、统一 reason、UUID、timings、普通 Python facade |
| `executor/backend.py`、`pipeline.py` | private InputBackend protocol、共享锁、fresh precheck、提交边界、恢复/cleanup |
| `actions/equipment.py`、`production_lines.py` | 装备 catalog、完整列表 diff / duplicate / identity reconciliation |
| `actions/snapshots.py`、`construction.py`、`politics.py`、`trade.py` | 通用临时身份、州/建筑/法律/顾问/贸易 catalog |
| `executor/*_ui.py`、`*_service.py` | 各领域确定性识别、操作、重复 readback |
| `executor/non_military_layout.py` | 集中管理当前固定 profile 的坐标与区域 |
| `scripts/build_phase3_templates.py` | 从本轮真实校准截图裁出模板/数字字形及贸易分数分隔符 |
| `scripts/phase3_client.py`、`phase3_domain_client.py` | 官方 SDK semantic client，readiness / freshness、逐项持久化与失败停止 |
| `scripts/summarize_phase3_live.py` | 只读聚合实机 JSON、状态/延迟/失败，写项目内汇总 |

复用 `reference/HOI4-AI` 的 deterministic scripted hand、template matching 与 capture/worker 隔离思路（参考 commit `73595d3`；项目 MIT / Apache-2.0 双许可，沿用模板适配的 MIT 说明）。复用本项目已有 worker、focus guard、独立 watchdog、capture、F12、emergency stop、Esc recovery、action lock、production snapshot。没有引入 PPO / BC / learned visual policy / self-play。

`@oai/sky` 仅在 Computer Use pump/backend 层；Domain Service 不 import vendor-specific API。仍依赖已授权 Computer Use 会话运行 pump，没有重写 native backend。快捷键优先，页面标题/template 验证后才进入目标；短促按键未被游戏采样时允许已识别 GUI 按钮 fallback。一次性校准使用真实截图，执行路径不依赖大模型逐步看图或视觉策略。

## Safety 与身份

- 只允许已绑定 `hoi4.exe`，每次输入验证 HWND / PID / process / foreground；失焦立即终止，不自动拉前台。
- F12 latch、独立 guard/watchdog 保持；guard 约 20 ms 轮询、watchdog 12 s、action 90 s、bridge 10 s。fresh telemetry 上限 30 s。
- backend 仅原子 click / key，不暴露 held input；release / end 释放内部状态、清空 capture、解除 guard。cleanup/end 意外异常也释放共享锁；已得到的 confirmed 证据与 cleanup failure 分开记录。
- 最多一次 mutation 提交，提交后从不自动重发。Trade 只有一次额外无输入 capture 等待已知弹窗重绘；后续成功实机结果 observation retry 0。
- 恢复 Esc 仅在 guard 仍允许输入时执行；Esc 漏采样不声称 modal 已关闭。未知 modal 停止，不提交其确认按钮。
- GUI 对象使用 session-local ID、snapshot version、120 s TTL、identity signature；拒绝过期/顺序改变/身份改变及 telemetry seq 回退。uncertain 会使 snapshot 失效，`stable_game_identity=false`。

操作者后续明确授权正常 GUI 启动/解除暂停，覆盖最初附件的对应限制；本轮游戏已经运行，没有执行启动。Mod 选择不改，没有 console / effect / direct save mutation，没有 `set_technology`、`research all`、`complete_national_focus` 或 `eval_effect`。

新增动作统一 PRECHECK → OPEN → LOCATE / VERIFY TARGET → SUBMIT → WAIT / READBACK → CONFIRMATION。结果区分 `rejected`、`failed`、`timed_out`、`uncertain`、`confirmed`、`already_satisfied`，含 `accepted`、`action_id`、`duration_ms`、`retry_count`、七段 timings、确认来源和原因。`accepted=true` 不表示成功；已经满足的目标不提交 mutation。旧 Research / Focus / factory-count 路径保留已验证实现，尚未完全迁移新结果格式。

## Live verification 与延迟

全部以下 confirmed 记录来自 **official SDK stdio → semantic API → Local Executor → 正常 GUI → repeated readback**。数值取 [实机汇总](artifacts/phase3/live-summary-20261002.json)，不混入手工校准、失败或 already_satisfied。恢复操作纳入次数；分段均值见该 JSON 的 `average_stages_ms`，total 包括 guard 与 cleanup，未必等于各段之和。

| Action | confirmed 次数 | 平均 total ms |
| --- | ---: | ---: |
| get_production_lines | 4 | 2746.25 |
| create_production_line | 2 | 10758.50 |
| reorder_production_line | 2 | 11055.00 |
| delete_production_line | 2 | 9601.50 |
| get_construction | 4 | 2007.75 |
| build | 3 | 13093.67 |
| cancel_construction | 6 | 7184.67 |
| change_construction_priority | 2 | 6250.50 |
| change_economy_law | 2 | 11875.00 |
| change_conscription_law | 2 | 17133.00 |
| get_advisors | 2 | 2218.50 |
| hire_advisor | 1 | 7782.00 |
| get_trade_state | 1 | 5796.00 |
| set_trade_import | 4 | 18867.25 |

提交 retry 合计 **0**。沙赫特重复 hire 为 already_satisfied（3359 ms）；Trade 重复目标 1 和 0 为 already_satisfied（6969 / 4610 ms）。后两次不再发送合同。

Production 在 session 3 创建步兵/支援两条；session 4 下移/上移；session 5 删除两条，最后列表恢复原八条与 20/28。Construction 正式创建州 64 军工、州 66 基建、州 65 民工各一栋，完成优先级调整及取消；六次取消还包括早期正常 GUI 校准队列的清理。法律各往返一次，沙赫特正式 hire 一次。

Trade 四次 confirmed：1→2（17172 ms）、2→0（19859 ms）、0→1（18844 ms）、1→0（19594 ms）。早期 0→1 实际提交后读数不确定，保留 uncertain，不重发；之后以重新读取的真实合同为下一动作基线。独立 `get_trade_state` 在正常读档后的 1936 年 1 月新鲜日帧确认成功。

## 失败与修复

原始 JSON 和截图全部保留，汇总包含 **10 条未成功 action**：

| 原始文件 | 状态 / 原因 | 处理 |
| --- | --- | --- |
| production-live-session-1 / -2、production-live-bridge-check | timed_out / ui_timeout ×3 | pump 初始固定等待时序失败；改为 readiness handshake，未放宽 safety deadlines |
| production-live-session-3 | rejected / target_not_visible | fold hover 与重排 crop 过小；中性位置 capture、真实模板修正，提交前停止 |
| production-live-session-4 | uncertain / unexpected_state_change | 未校准删除 modal；未点确认，明确 Cancel 后以新 snapshot 重试独立请求 |
| construction-live-cleanup-1 | rejected / telemetry_stale | 未产生新 daily frame，输入前停止；正常推进后再读 |
| construction-live-cleanup-2 | uncertain / unexpected_state_change | 未知取消 modal，未提交 OK；补充州名/建筑/标题验证，恢复后新请求成功 |
| politics-live-1 | timed_out / ui_timeout | laws 后 pump 会话已结束，get_advisors 没有 hire；新短会话成功 |
| trade-live-one-1 | uncertain / readback_ambiguous | 实际 1 民工 / 8 钢铁，8/8 被旧数字解析混读；新增分数分隔识别/独立读数真实样本回归，无自动重发 |
| trade-live-zero-1 | rejected / identity_mismatch | proposal 重绘导致提交前身份不符，真实合同仍为 2；一次无输入重绘等待，后续独立请求成功 |

顾问手工校准时曾误认为 picker 还有下一步，正常点击已立即雇用沙赫特并花 75 PP；当时明确记录，正常 GUI 移除后恢复空槽，再进行正式 SDK hire。该手工动作不算正式成功；最终原档恢复顾问与 PP。

自动审批曾拒绝不明 modal 固定坐标点击：先取得独立当前按钮/身份证据再执行。曾因旧 Phase 3A “不做 Trade”拒绝本轮 Trade CLI；完整读取最新用户附件第 2 / 7 / 15 节明确授权后再按当前范围执行。事件窗口只使用已核对的最小化按钮，没有借此选择外交选项或绕过审批；目前没有 action 被审批持续阻塞。

Windows sandbox 曾拒绝 stdio named pipe / 默认 pytest temp：使用审核通过的受控 CLI 和项目内独立 basetemp。增加工具后旧 MCP 测试仍期望 23 个而失败两项，更新为当前 25 tools/schema 后通过。所有这些失败不隐藏，也不计为 confirmed。

## Offline regression

最终 **194 passed / 10 subtests passed**，用 mock worker / fake telemetry / 真实截图 fixtures 覆盖 catalog、create/delete/reorder、重复身份、旧 snapshot、Construction diff、法律 PP/要求/disabled、顾问槽/身份、Trade 数量/不足民工/读数分歧及六种结果。

原 Phase 1 / 2 / 3 测试继续通过；跨领域覆盖 stale、focus loss、F12、watchdog、timeout、backend failure、no double-submit、snapshot invalidation、semantic schema / Python API 不接受 raw coordinates。新增回归还验证未知灰色队列尾部不被误判为空、顾问 disabled red cross、cleanup 异常不锁死下一动作。

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=artifacts/phase3/test-temp-wrapup
.venv/Scripts/python.exe -m compileall -q src scripts tests
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe scripts/build_phase3_templates.py
.venv/Scripts/python.exe scripts/summarize_phase3_live.py
git diff --check
git -c core.whitespace=cr-at-eol diff --cached --check
```

compileall、pip check、模板重建、汇总生成与 diff 检查通过。原始证据依 `.gitattributes` 保持 Windows CRLF 字节；完整 staged diff 按 `cr-at-eol` 检查通过，未修改原始 JSON 内容或换行。没有项目外部 review 脚本，没有增加额外 review 流程。F12 / loss of focus / watchdog 的历史实机证据保留，本轮没有再次触发这些危险故障；当前代码离线回归覆盖它们。

## Profile、恢复与最终状态

本机 HOI4 1.19.3 / 原生中文 / 仅 Telemetry Mod / 2560×1080 / scale 1.0；GER 1936 开局。为合法 PP 和校准正常推进到 1937 年，主要测试最后日期为 1937-04-27，不冒称所有 live 在 1936 年完成。州操作要求原固定相机及 Copenhagen anchor 校验；不支持任意缩放/平移。

先正常 GUI 恢复原军工八条/20–28、空建筑队列、法律和零 SWE 钢铁进口，再通过游戏 Load 菜单读 `GER_1936_01_01_12.hoi4`。第一次完整恢复已验证 **1936-01-01 12:00 / paused**；同一 reader 验证顾问三槽为空、建筑队列为空。截图：[地图](artifacts/phase3/captures/restored-map.jpg)、[顾问](artifacts/phase3/captures/restored-politics.jpg)、[建筑](artifacts/phase3/captures/restored-construction.jpg)、[第一次恢复最终画面](artifacts/phase3/captures/restored-final.jpg)。

独立 Trade getter 验收随后短暂正常推进，SDK 查询新鲜 GER 1936 年 1 月 2–3 日帧；确认零合同及零目标 already_satisfied。之后再次通过正常菜单选择同一原档并提交 Load，最后观察是加载画面。收尾复核时窗口已最小化，capture 返回 `window is minimized`；遵守 no auto refocus，因此**第二次加载完成后的画面/暂停状态 UNKNOWN**，不拿第一次截图或旧日志伪称最终 live。

[恢复记录](artifacts/phase3/restoration.json)保留两次恢复的证据边界。8 个原存档 SHA256（含 autosave）以及 `dlc_load.json` 的 Mod 选择 SHA256 与基线相同；没有直接保存/覆盖/修改存档。原 autosave 的只读备份位于 ignored `artifacts/phase3/save-backup`。实机客户端已退出，临时 bridge endpoint 已关闭。

恢复后未验证新的日帧；晚于原档的缓存仍是旧时间线，不能用于下一动作。下次操作前需正常推进 fresh telemetry 并重新建立 session snapshot。本轮实现、测试、文档、模板和实机证据一并纳入 Phase 3 提交，运行时凭据、存档备份和临时测试目录排除；远程为 `https://github.com/shingoxy/HOI4_AI_MCP.git`。

## Remaining UNKNOWN 与 Phase 4 entry

- 完整 research 槽映射/剩余时间、active focus ID、逐线生产内部 ID/效率/产量、建筑完整 progress、全贸易 telemetry。
- 其他分辨率、语言、Mod 组合、任意州/任意资源/任意装备和滚动列表的稳定性。
- 当前 chat 新 action 注册、其他厂商真实 Agent 客户端；vendor-neutral schema 和 Python facade 离线验证通过，不等于已运行全部厂商。
- Computer Use pump 是当前 backend 技术债；独立 native service、完整 Agent Adapter 和旧动作统一结果格式尚未实现。
- 第二次读档的最终 GUI 复核因最小化未完成，最终新鲜 telemetry 未取得。

本轮所需关键动作均有正常 GUI 实机闭环，限定 Phase 3 已达到验收标准。Phase 4 需另行明确范围、军队对象身份/观察契约、动作 legality 与同等 safety regression；本轮**到此停止**，没有 Phase 4 实现。
