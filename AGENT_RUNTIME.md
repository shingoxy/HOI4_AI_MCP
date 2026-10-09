# Phase 5 Agent Runtime

## 2026-10-07 Time Ownership / Safe Stop 合约

时间控制修复后的验收见 [Time Safety gate](artifacts/phase5/time-safety-20261007/TIME_SAFETY_GATE.md)。A/B 实机通过，C 为离线失败分支测试；它们不计 Agent 战略行为。下方 tool-20261007 checkpoint 保留为历史。

| 状态 | owns_running | 含义 |
|---|---|---|
| UNKNOWN | false | 尚无确认的暂停 / 运行证据；不得据此恢复 |
| PAUSED_CONFIRMED | false | GUI 暂停读回成立，允许释放停止责任 |
| RUNNING_OWNED | true | Runtime 在可能恢复时间的输入之前取得停止责任 |
| STOPPING | true | 独立有界停机正在执行，尚未确认暂停 |
| STOP_FAILED_OWNED | true | 停机失败或不确定；保留责任、停止计划并要求人工介入 |

`owns_running` 由状态派生，不能在 finally 中无条件清空。只有 GUI clock glyph stability 或已校准菜单的确定性暂停证据，才能进入 PAUSED_CONFIRMED。telemetry 只证明日期 / freshness；GUI 日期仍可 UNKNOWN。

`ensure_game_stopped()` 独立于 Agent 战略循环。advance 的异常/finally/watchdog、bootstrap 失败、Runtime pause/circuit/退出和 NativeRuntimeHost.close 均先执行停机，再清理。每次 ownership acquisition 最多一次正常 pause Space；失败后最多一次已校准 stop-only route。再次调用只能被动重观察暂停，不重发 Space / Escape；未知或叠层 modal 不自动 dismiss。现有前台、PID/HWND、geometry、F12 和 timeout guard 仍生效。

正常暂停失败先保存精确失败 RGB、clock/modal/menu ROI、UTC、telemetry、ownership 和 foreground 信息，再尝试恢复。捕获受 guard 拒绝时明确 exact_rgb_available=false；输入抛错后不能沿用先前 RGB。证据写盘失败不抹去 ownership，也不阻止独立停止尝试。

close 仍 owned 时报告 `shutdown=unsafe_stop_failed`、`game_pause=UNKNOWN`、`operator_intervention_required=true`；不能报告 clean。暂停确认和所有权释放分别审计，记录 acquired/released、pause attempts/failures、safe-stop attempts/successes、modal/unknown 计数及人工安全干预。

首个国家自治目标及后续验收路线见 [COUNTRY_AUTONOMY_PLAN.md](COUNTRY_AUTONOMY_PLAN.md)，属于后续计划；当前有限 Scripted targets 不代表国家战略能力。

修复后的新Construction single实机confirmed，但新30天在奥林匹克World News停止失败：7 confirmed日、STOP_FAILED_OWNED、unsafe_stop_failed，需人工安全暂停。known新闻尚无校准stop-only route；真实Codex未进入。详见 [当前Phase5结果](PHASE5_AGENT_RUNTIME.md)。不能把ownership正确保留等同于停机覆盖已完整。

## 前一轮 tool-20261007 checkpoint（历史保留）

更新日期：2026-10-07。本轮checkpoint。

**Phase 5：IN PROGRESS / CONSTRUCTION TOOL NAVIGATION CONFIRMED / CONSTRUCTION ACCEPTANCE BLOCKED BY BOOTSTRAP MODAL PAUSE FAILURE。** 尚未达到“能用”。新30天及真实Codex未运行，实际模型调用0。旧seven-action 7/7、Production reader、Scripted single、7天及原21/30失败历史均保留，未重做。

本轮完整回归 **554 passed /10 subtests，60.96s**（原531保留，新增23）；相关79 passed，22.23s。原0.9模板、90%几何一致率、一像素位移、局部>=10和Production阈值保持。未commit/push、接其他模型或使用Computer Use；pump全程OFF。

| 本轮验收 | 真实结果 |
|---|---|
| 工具只读诊断 | 两组civilian和一组military，各只选工具一次，未点击建设州，queue前后[]。保存full RGB、ROI、首帧/稳定帧、map/modal/mode和原始NCC；不能把旧失败瞬间RGB的缺口改写成已补回 |
| 工具根因 | 旧selected模板在未激活工具时也匹配0.9594；实际激活后随边框循环动画在0.8959～0.9689变化。安装游戏GUI定义的start_construction_overlay引用两帧1.5fps循环sprite，与实机采样相符。hover、pulse和selected不能只凭一次NCC区分；没有证据证明DPI/GDI缩放、cursor或sprite替换为根因 |
| Reader | TOOL_NOT_SELECTED / SELECTED / ANIMATING / OCCLUDED / UNKNOWN。civilian图标core NCC>=.9、四边选中轮廓及正向construction mode联合确认，两次独立正向观察。最多3秒/12帧被动采样，不重发工具click；错误MIL工具或未知/遮挡拒绝。GDI cursor证据仍UNKNOWN。所有阶段先存PNG/ROI/JSON，Operator私有proof保存详细证据，provider history不接收 |
| 几何采样覆盖 | 新帧在1500-feature预算下局部只有7～9匹配；3000预算下局部20、全图93.8%～94.2%。只增加特征提取覆盖，不改变原匹配/位移/count阈值、目标点/区域或camera范围；小/大pan及遮挡仍拒绝 |
| 实机工具导航 | **TOOL_NAVIGATION_CONFIRMED**；一次工具click、两次正向truth，最终MAP_READY：665/714、93.14%、state64局部21。state64/GER独立身份、queue前后[]、paused=true；GDI physical2560×1600/DPI120，SendInput，0 semantic commit。结果先落盘后才启动新Agent session |
| 新Construction session | run **69144e62-4e5a-4f75-914d-3ec335360448**：**BLOCKED BEFORE AGENT**，wall5.156s；observations0 / decisions0 / actions0 / results0 / confirmed0 / rejected0 / uncertain0 / mutation0。build及queue mutation readback根本没有进入，不能算Construction confirmed或action rejected |
| 直接阻断 | fresh bootstrap **failed / modal_blocked / paused=false / 4687ms**。fresh telemetry已到1936-05-01，但正常暂停因modal抛错。Native trace只有一次Space resume，没有成功pause输入。GameTimeController.pause_owned在finally无条件清空owns_running，即使pause失败；close不再拥有停止路径，这是实质时间安全缺陷。此次没有自动retry或再次提交build |
| 后续安全处理 | 游戏在bootstrap失败后继续走时。之后真实截图包含新闻及科研完成叠层；该later frame不是精确bootstrap失败帧。操作者仅做**一次Escape安全暂停**，已校准菜单NCC1.0；随后独立只读确认paused=true、resumable=false。没有人工战略动作，但有1次人工安全干预，不能宣称无人工运行 |
| 时间证据 | bootstrap结束日期1936-05-01来自run内fresh telemetry；收尾日志最后已到**1936-08-03**，但状态stale/log_mtime_upper_bound，只作last-known。GUI日期解码UNKNOWN；额外推进的时间全部不计benchmark，game_days仍0，不把它伪装成30天成功 |
| 地图审计 | prepare/require/capability和recovery起止单独记入native trace。Find View→Go to Capital→bounded wheel的attempt/success/failure/duration独立汇总，不隐藏于action duration。新session未进入观察，map各计数0；导航诊断的计数另列verification。无自动clock recovery route，clock_recovery_count=0 |
| 新30天 / 真实Codex | **全部NOT RUN**；Construction mutation gate前的时间安全gate失败后停止。真实provider boundary实现/新测试与真实推理不能提前接入，历史fake测试仍仅offline。无截图/坐标/backend进入任何模型 |

收尾9个手动存档、autosave与Mod哈希均未改变，无新增/删除，0 console/effect/memory/save编辑。首次收尾helper因host.templates属性错误未完成pause字段；原日志和PNG保留，第二次只读检查改为实际clock模板路径，已确认菜单暂停。当前NativeMapState在later未知叠层弹窗帧仍可能返回MAP_READY，不能据此宣称通用modal覆盖。

**剩余blocker：**先修复模态下时间ownership与独立停止路径，并保存clock失败精确RGB；明确未知/叠层modal的fail-closed范围。需新的fresh baseline后重新进行一次Construction mutation验收，再按30天→真实Codex→3–5 cycles顺序。依本轮附件停止规则，此checkpoint不继续修复或重跑gate，等待下一步。不得用工具导航成功或554项离线测试代替完整Construction/长期/模型实机验收。

证据：[verification](artifacts/phase5/tool-20261007/verification.json)、[工具真实诊断](artifacts/phase5/tool-20261007/diagnostic-2/result.json)、[实机工具导航](artifacts/phase5/tool-20261007/selector-native-1/result.json)、[新session](artifacts/phase5/tool-20261007/construction-single-1/summary.json)、[bootstrap事件](artifacts/phase5/tool-20261007/construction-single-1/events.jsonl)、[安全暂停](artifacts/phase5/tool-20261007/safety-stop-1/result.json)、[最终只读](artifacts/phase5/tool-20261007/final-readonly-2/final-state.json)、[完整回归](artifacts/phase5/tool-20261007/pytest-full-1.txt)。

## 前一轮checkpoint（保留历史，工具修复之前）

更新日期：2026-10-07。

## 2026-10-07 当前停止点

**Phase 5：IN PROGRESS / MAP AND CLOCK REPAIR OFFLINE TESTED / CONSTRUCTION REVALIDATION FAILED。** 尚未达到“能用”。原seven-action 7/7、新Scripted工厂单轮confirmed和7天有限稳定性保留；原30天第21日失败不改写。本轮新的Construction单轮在提交前返回rejected / requirements_not_met，mutation_submitted=false、retry0；按用户附件“若任一关键验收失败，停在当前安全checkpoint”停止。新30天、真实Codex及multi-cycle均NOT RUN。


Native host在empty construction queue后只读验证当前map和state64/GER身份；Catalog返回各项readiness。最终提交仍独立重做地图/身份/选中工具检查，mode切换用同位置场景特征验证，不计算目标坐标。MAP恢复一次且经guard；恢复失败不会被伪装为成功navigation继续跑benchmark。该机制只读校准及531项回归通过，但新真实Construction单轮在selected-tool确认返回requirements_not_met，0提交，当前仍非可用验收状态。

Runtime沿原policy失效snapshots、summary重观察、quarantine并PLAN_STOPPED，没有retry。readback/confirmation未进入；不会把空队列、later observation或只读drawing4当mutation confirmed。新30天/Codex/provider/multi-cycle全部NOT RUN；旧21天failed run不改。下一步仅是调查工具状态与精确失败帧，不自动重复当前proposal。Clock暂停证据和telemetry日期来源独立，GUI日期不解析则明确UNKNOWN。

当前报告：[本轮验证](artifacts/phase5/stability-20261007/verification.json)、[Construction run](artifacts/phase5/stability-20261007/construction-single-1/summary.json)、[事件和Operator proof](artifacts/phase5/stability-20261007/construction-single-1/events.jsonl)、[只读收尾](artifacts/phase5/stability-20261007/final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。

最终完整复核 **531 passed /10 subtests，46.85s**：[pytest-final2.txt](artifacts/phase5/stability-20261007/pytest-final2.txt)。前一次收尾复核有1项summary.tmp替换WinError5（530 passed）；原日志保留，相同失败组4/4及随后全量均通过，暂时权限/占用错误的根因仍UNKNOWN，未修改Runtime策略。

## 前一轮checkpoint（保留历史）

更新日期：2026-10-07。全量 **493 passed / 10 subtests passed**；新的Scripted单轮11→12已confirmed，7天有限Runtime稳定性通过（2次valid no-op，战略覆盖不足），30天在实际第21日因build/map_target_unresolved rejected停止。真实Codex未进入；详细证据见 [PHASE5_AGENT_RUNTIME.md](PHASE5_AGENT_RUNTIME.md)。2026-10-06的uncertain与later readback历史未改写。

single验收由host CLI检查，保持AgentRuntime的failure/quarantine/circuit策略不变：必须至少一个mutation_submitted=true且status=confirmed的结果、无circuit pause，并有fresh有效post-action strategic observation、WindowsNativeBackend/pump OFF。空decision、already_satisfied、uncertain后的later readback不能替代confirmed mutation。只有成功mutation后才做正常GUI fresh bootstrap和后置观察，单独审计且不计benchmark游戏日；任何失败不进入7天。

Scripted原规则只向上推荐10/11/12，目标保持12；实际12时允许valid no-op，不计mutation gate通过。用户单独授权的操作者12→11准备已独立confirmed，不计Agent行为；后续全新session自主11→12通过。Native getter对infantry_equipment_1目标要求numeric AND grid AND 完整列表/global MIL重复一致；其他行numeric/global scope保持partial。reader等待最多两秒且仅捕获，没有submit retry。

RunAudit记录confirmed、already_satisfied、mutations_submitted、confirmed_mutations、timed_out、backend_errors、timeline_reset，并保留timeouts。research/focus/construction_queue_idle_days只记录可靠idle观察日期与known dates，不推算连续24小时；unused_MIL_observations分known/unused/unknown，stale/unknown不计为闲置。新single及既有scheduler/time/circuit/bounded history/no duplicate、Codex semantic adapter/pump OFF有离线测试；真实single/7天已执行，30天仅到21日，真实Codex尚未执行。

`agent_runtime.py` 与 AI provider 和 GUI Executor 分离：

```text
OBSERVE → DECIDE → VALIDATE → EXECUTE → VERIFY → ADVANCE → OBSERVE
```

`agent.py` 定义 vendor-neutral `AgentAdapter / AgentDecision`。ScriptedAgent 与 CodexAdapter 都只接收 observation、catalog 和 history。Scripted 按 deterministic priority 选择一个可靠未满足目标，复用相同 Runtime/Operator 路径；没有 GUI、backend 或直接 state mutation 权限。

Runtime 默认每 cycle 最多 3 个 mutation；Scripted 首版每次只提出 1 项。schema/catalog/policy 校验后排序，每项提交前再校验 catalog/freshness。结果先写入 JSONL 并更新独立 summary，随后才能执行下一项。confirmed 由既有 Operator 的 deterministic readback 确立，Runtime 不把 accepted 或 submitted 当成功。

uncertain/failed/timed_out：停止计划、失效 snapshots、summary 重观察、隔离该语义 proposal；不执行后续依赖项或自动重发。Operator 意外抛出异常时，输入是否发生设为 UNKNOWN，按 uncertain 处理。rejected 记录 identity/stale/unsupported/temporary 分类；unsupported 从 Runtime 目录移除。rejected 的 already-satisfied reason 允许继续，但审计仍保存原 rejected，不伪造 confirmed。

连续 3 uncertain、5 rejected、3 backend errors，以及 stale telemetry、失焦/F12/watchdog，触发 `AGENT_PAUSED`。只有 controller 仍拥有运行时间且 GUI guard 允许时才尝试暂停。窗口失焦不自动 refocus，F12 不绕过，不能安全暂停时记录失败。

`game_time.py` 提供有限 `advance_days`；私有 `NativeClockGUI` 只使用正常 GUI。先确认暂停并安装独立 20 秒 stop path，再 resume，等待 fresh telemetry 的日期前进，再 pause 并确认。timeout、回退/日志重建或暂停未确认都会停止。每个游戏日使用 cheap summary；每 7 日或新重要告警进行 strategic decision，不每日调用 provider。日期的中文 `24:00` 按次日 00:00 解析。时间控制仍需实机 gate，离线模拟不证明实际 HOI4 timing。

timeline reset、日期回退、日志重建清除 plan、GUI snapshots、pending triggers、quarantine、unavailable overrides、history pointers、goals 和 decision schedule；保留 run audit。provider history 上限为 20 decisions / 50 results / 8 current goals / 20 important events。

`CodexAdapter(provider)` 已覆盖fake-provider严格JSON、坏JSON、未知动作、非法目标、timeout和超预算测试。**尚未连接真实Codex provider。**本轮在Scripted 30天gate第21日停止，未进行真实Codex decision/action或多轮测试。CLI/ChatGPT登录与官方程序调用路径已只读核对，仍需验证输入/工具隔离及实际推理。不能把callback/fake provider测试算真实模型接入，没有接其他AI。真实provider须只获得Observation/Catalog/Goals/History，不得获得截图、坐标、GUI backend或CU能力。

接续实机顺序：observation → catalog → Scripted single cycle → Scripted 7 days → 稳定后 Scripted 30 days → Codex decision → 至少一项 native confirmed → limited multi-cycle。任一不稳定点停止。

由操作者配置窗口和 reference；Agent 不接收以下 CLI 配置：

```powershell
.\.venv\Scripts\python.exe scripts/run_agent_runtime.py --window <current-window> --mode observe --output artifacts/phase5/runtime-<run>/observation --paused-reference artifacts/phase5/gate-20261006/final/native-final-physical.png
.\.venv\Scripts\python.exe scripts/run_agent_runtime.py --window <current-window> --mode single --output artifacts/phase5/runtime-<run>/single --paused-reference artifacts/phase5/gate-20261006/final/native-final-physical.png
.\.venv\Scripts\python.exe scripts/run_agent_runtime.py --window <current-window> --mode days --days 7 --output artifacts/phase5/runtime-<run>/days7 --paused-reference artifacts/phase5/gate-20261006/final/native-final-physical.png
```

每次输出必须使用新目录。host 不启动游戏、不切换窗口、不改 Mod、不保存或改 save。paused telemetry 陈旧时，通过独立有界 GUI bootstrap 取得 fresh frame；bootstrap 独立记录，不计 benchmark 的游戏日。Scripted benchmark 记录 run ID、起止日期、observation/alerts/decision/action/result 数量、失败统计、circuit breaker、wall time、game days 和 pump 状态。

当前证据：[单轮confirmed](artifacts/phase5/continuation-20261007/scripted-single-1/summary.json)、[7天有限稳定性](artifacts/phase5/continuation-20261007/scripted-days7-1/assessment.json)、[30天第21日停止](artifacts/phase5/continuation-20261007/scripted-days30-1/assessment.json)、[完整验证](artifacts/phase5/continuation-20261007/verification.json)、[菜单暂停证明](artifacts/phase5/continuation-20261007/pause-menu-proof.json)。7/30天评估分别记录真实日数、schema/catalog合法决策、valid no-op、真实action attempt及coverage，不凭日期前进宣称完整自主战略验收。build被拒绝前未提交mutation，retry0、snapshot失效/重观察/quarantine/停止正确，尚未继续或修复绕行。真实Codex模型及semantic/native action均NOT RUN。seven-action gate仍7/7，未重跑，原存档/Mod哈希不变，无commit/push。
