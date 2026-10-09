# 项目状态

## 2026-10-09 提交 checkpoint

**Phase 5：IN PROGRESS / MODAL STOP-ONLY MATRIX OFFLINE TESTED / WORLD NEWS LIVE GATE PENDING。** seven-action 7/7、Scripted 单轮 mutation、Construction 单轮、有限 7 天及 Time Safety A/B 实机结果保留；原21/30与最新7个confirmed推进日的失败记录不改写。本次提交前完整回归为 **604 passed / 10 subtests passed，82.95s**：[日志](artifacts/phase5/commit-20261009/pytest-full-1.txt)；compileall、pip check 通过。沙箱临时目录 WinError 5 的历史失败日志也保留。

新增六态 stop-only Matrix 保留旧 reader 分类；新停止路径须匹配 immutable live proof、PNG 哈希、双次菜单暂停及退出菜单后 modal identity 不变。**World News 尚无实机证明，stop_route 仍 none。** 最近只读 preflight 为 loss_of_focus / pause UNKNOWN，未发送输入；本次提交准备也不操作 HOI4。

最新用户计划已取代历史“任一 gate 失败即停”规则：普通代码或校准失败保留证据后修复、回归、重测；真实外部阻塞或无法安全暂停时交操作者处理。顺序仍为 World News 独立安全停止 gate → fresh paused / NO_MODAL baseline → 新 Scripted 30 天 → 真实 Codex mutation 和有限多周期 → 一个非 Codex 模型 → 德国1936和平经营180天；全部属于 Phase 5，已通过 Construction 不为制造证明而重做。[执行 checkpoint](artifacts/phase5/final-execution-20261007/CHECKPOINT.md)

本次提交包含源码、文档、模板、测试必需截图、关键实机证据与日志；其余大截图保留本地，完整路径、大小与哈希见 [证据清单](artifacts/phase5/commit-20261009/evidence-inventory.json)。维持 pump OFF、正常 GUI、原 save / Mod 边界。以下章节为历史 checkpoint。

## 2026-10-07 时间安全修复后 checkpoint

**Phase 5：IN PROGRESS / TIME SAFETY A+B CONFIRMED / SCRIPTED CONSTRUCTION CONFIRMED / NEW 30-DAY GATE FAILED。** 尚未达到无人值守可用；真实 Codex 未运行，模型调用 0。保持现有五阶段，旧 seven-action 7/7、Production reader、single / 7-day 和原 21/30 失败全部保留。

- 修复 time ownership：暂停失败后保留 STOP_FAILED_OWNED；advance/watchdog/bootstrap/circuit/退出均走独立有界停机。未知 / 叠层 modal 拒绝输入；精确失败 RGB 与 ROI 在恢复前保存，guard 捕获失败明确 unavailable。
- Time Safety A/B 实机通过，C 仅离线；新 paused / NO_MODAL / fresh frame_received_at baseline 通过。[逐项证据](artifacts/phase5/time-safety-20261007/TIME_SAFETY_GATE.md)
- 新 ScriptedAgent Construction：**confirmed**，自主 build(state64,civilian_factory,1)，一次提交、13094 ms、retry 0；fresh 后置观察通过，退出暂停确认、ownership 释放。[单轮](artifacts/phase5/time-safety-20261007/construction-single-1/assessment.json)
- 新 30-day run：**失败，7 个 confirmed 游戏日**；1936-08-08→08-16 的 fresh 日期差为 8 天，但第 8 次推进未确认暂停，不能计通过。12 次观察 / 2 次 valid no-op / 0 战略动作，wall 96.485s；不算自主战略成功。[原始 summary](artifacts/phase5/time-safety-20261007/scripted-days30-1/summary.json)
- 实际阻断：奥林匹克新闻 KNOWN_BLOCKING_MODAL，stop_route=null；正常 pause 被阻挡，有界 safe stop 不发送未校准 Escape。acquired/released=9/8，pause_failure=1、safe_stop=1/0、modal_count=4（非四个独立弹窗）、circuit=time_stop_failed。保留 ownership；诚实报告 **unsafe_stop_failed / pause UNKNOWN / operator intervention required**。
- 已请求人工安全暂停。当前只读 checkpoint 尚未确认暂停；日志最后到1937-01-11，来源为 log_mtime_upper_bound，只作收尾 last-known，额外时间全部不计 benchmark。原9个手动存档、autosave、Mod哈希无变更，无新增/删除。[只读收尾](artifacts/phase5/time-safety-20261007/final-readonly-1/final-state.json)

完整回归 **585 passed / 10 subtests，75.34s**，保留原554并新增31项 time safety tests；compileall 通过。全程 GDI physical 2560×1600/DPI120、SendInput、**Computer Use pump OFF**；无console/effect/memory/save编辑、其他模型、commit/push。按附件失败即停规则，本轮不修新 modal route、不重跑30天、不进入真实 Codex / multi-cycle。

下一步先在停止的测试 baseline 上验证这个已知新闻 modal 的有界 stop-only 路径，恢复确定性停机覆盖，再重新按30天→真实Codex→3–5 cycles验收。国家自治的后续路线已写入 [COUNTRY_AUTONOMY_PLAN.md](COUNTRY_AUTONOMY_PLAN.md)：先德国1936和平经营半年，再陆战、空海军、其他国家；本轮只规划，未扩大动作范围。

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

**Phase 5：IN PROGRESS / MAP AND CLOCK REPAIR OFFLINE TESTED / CONSTRUCTION REVALIDATION FAILED。** 尚未达到“能用”。原seven-action 7/7、新Scripted工厂单轮confirmed和7天有限稳定性保留；原30天第21日失败不改写。本轮新的Construction单轮在提交前返回rejected / requirements_not_met，mutation_submitted=false、retry0；按用户附件“若任一关键验收失败，停在当前安全checkpoint”停止。新30天、真实Codex及multi-cycle均NOT RUN。

当前报告：[本轮验证](artifacts/phase5/stability-20261007/verification.json)、[Construction run](artifacts/phase5/stability-20261007/construction-single-1/summary.json)、[事件和Operator proof](artifacts/phase5/stability-20261007/construction-single-1/events.jsonl)、[只读收尾](artifacts/phase5/stability-20261007/final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。

最终完整复核 **531 passed /10 subtests，46.85s**：[pytest-final2.txt](artifacts/phase5/stability-20261007/pytest-final2.txt)。前一次收尾复核有1项summary.tmp替换WinError5（530 passed）；原日志保留，相同失败组4/4及随后全量均通过，暂时权限/占用错误的根因仍UNKNOWN，未修改Runtime策略。

## 前一轮checkpoint（保留历史）

更新日期：2026-10-07

## 当前阶段

**Phase 5：SCRIPTED SINGLE MUTATION CONFIRMED / 7-DAY RUNTIME STABILITY CONFIRMED WITH LIMITED STRATEGY COVERAGE / 30-DAY GATE STOPPED AT DAY 21。** seven-action gate仍7/7，未重跑；Scripted目标仍为Kar98k 12，未改为11。本轮用户单独授权的12→11准备已独立confirmed，不计Agent成绩。

| 本轮步骤 | 真实结果 |
|---|---|
| 独立GUI准备 | 12→11一次；原setter及独立getter均confirmed；paused；role=operator_test_preparation |
| 新Scripted单轮 | **confirmed**；fresh observation/catalog/session，自主11→12一次；duration 13391 ms、retry 0；fresh后置观察通过 |
| 7游戏日 | 1936-03-31→04-07，82.657s；11观察、2有效决策均valid no-op、0动作/错误/战略人工干预；实际7天，目标12重复确认。只证明有限Runtime稳定性，战略动作覆盖不足 |
| 30游戏日 | **未通过，实际21天**：1936-04-08→04-29，211.203s；28观察、4有效决策（3 no-op）、1 build attempt，0 confirmed / 1 rejected / 0 uncertain / 0 timed_out；PLAN_STOPPED，无circuit pause |
| 真实Codex | **NOT RUN**；因前一gate失败停止。官方SDK/CLI路径及本机CLI/ChatGPT登录只读核对完成，不等于真实provider或semantic action验收；fake callback仍不算真实模型 |

失败动作 `325bff43-716c-480e-b753-ad14b1b59198`：Agent在队列为空后自主选择state64/civilian_factory/count1，schema/catalog合法；native提交前地图锚点校验返回 **map_target_unresolved / rejected**，duration3000ms、mutation_submitted=false、retry0。Runtime失效snapshot、summary重观察、隔离proposal并停止；没有重发、绕过校准或继续跑满30天。下一步先在现有physical profile/state64范围内调查地图校准/视口失配，再重新评估30天及真实Codex gate。

全程GDI physical 2560×1600/DPI120、SendInput、**pump OFF**；没有console/effect/save编辑、Mod变更或commit/push。普通clock reader收尾返回clock_header_unrecognized，原记录保留；另一只读检查以既有game-menu模板NCC=1.0（阈值0.9）确认菜单暂停。10个原存档及Mod哈希均未变。完整回归 **493 passed / 10 subtests passed**，保留原483并新增10项准备脚本的单次提交/错误停止测试。

证据：[Phase5报告](PHASE5_AGENT_RUNTIME.md)、[本轮验证](artifacts/phase5/continuation-20261007/verification.json)、[single](artifacts/phase5/continuation-20261007/scripted-single-1/summary.json)、[7天评估](artifacts/phase5/continuation-20261007/scripted-days7-1/assessment.json)、[30天事件](artifacts/phase5/continuation-20261007/scripted-days30-1/events.jsonl)、[暂停菜单证明](artifacts/phase5/continuation-20261007/pause-menu-proof.json)。没有宣称完整自主战略验收成功，也未扩大整个项目Computer Use optional的表述。

## 2026-10-06 reader / single-cycle checkpoint（历史）

**Phase 5：IN PROGRESS / PRODUCTION READER READ-ONLY CONFIRMED / SCRIPTED SINGLE GATE NOT PASSED (ZERO MUTATIONS)。** 当前Kar98k工厂数确定为 **12**：numeric AND 15-cell grid AND 完整八行合计/header 22/28，重复读回一致。原11→12 action仍为uncertain，仅新增later_readback=12。本轮未重发setter、未重跑seven-action gate、未修改Runtime failure policy或Scripted策略。

修复真实GDI joined `2/` glyph，保留0.84/0.10/grid 0.85阈值；展开/折叠读回采用guard内两秒被动捕获与既有neutral导航。目标numeric/grid/global矛盾返回readback_ambiguous，不使用OCR/LLM reader。最终全量 **483 passed / 10 subtests passed**，原452保持；compileall/pip check/diff check通过：[verification.json](artifacts/phase5/reader-20261006/verification.json)。

新 [Scripted single-cycle #2](artifacts/phase5/reader-20261006/scripted-single-2/summary.json) 使用fresh observation/catalog/snapshots；1936-03-27、19.375s、2 observations、1 valid decision、**0 mutation**，无rejected/uncertain/timeout/backend error/timeline reset/circuit pause，pump OFF。当前12已到有限目录上界，原策略只向上推荐，Agent提出空actions。零动作不能过single gate；7/30天与真实Codex均NOT RUN。已询问benchmark前固定维持11的策略选择，未收到回答前不改规则。

只读收尾确认游戏暂停、Kar98k=12、原10个存档和Mod选择哈希不变，无新增/删除；没有commit/push：[final-state.json](artifacts/phase5/reader-20261006/final-state.json)。停在安全checkpoint，下一步需确定Scripted目标规则并通过有confirmed mutation的新单轮，才能进入7→30→Codex。详见 [Phase 5报告](PHASE5_AGENT_RUNTIME.md)，不扩大Computer Use optional表述。

## 前一轮 Runtime checkpoint（历史）

**Phase 5：IN PROGRESS / RUNTIME OFFLINE TESTED / SCRIPTED SINGLE-CYCLE UNCERTAIN。** 已实现 strategic observation、有限 Action Catalog、独立 AgentRuntime、ScriptedAgent、有限时间控制和 CodexAdapter 的 semantic/fake-provider 边界。MCP 新增两个语义接口，共 52 tools；不意味着全部工具 native live verified。

完整回归 **452 passed / 10 subtests passed**，保留原 389 项并新增 63 项；compileall、pip check 通过。报告：[Runtime API](AGENT_API.md)、[运行规则](AGENT_RUNTIME.md)、[验证记录](artifacts/phase5/runtime-20261006/verification.json)。首次完整测试的工具清单预期已按新增接口修正；所有旧功能测试保留。

初次 preflight 的 loss_of_focus 记录保留。用户保持前台后，[observation/catalog checkpoint](artifacts/phase5/runtime-20261006/observation-2/summary.json) 通过，四个页面串行读取并恢复安全页面；随后 [Scripted single-cycle](artifacts/phase5/runtime-20261006/scripted-single-1/summary.json) 自行选择 Production 11→12，提交一次，返回 **uncertain / production_number_unreadable / 7797 ms**。Runtime 停止计划、失效缓存并重新观察，retry 0，没有重发或人工选择动作。native GDI physical / SendInput left click / pump OFF；数字读回缺口尚未修复，实际 after count 保持 UNKNOWN，不能计 gate 通过。

按规定顺序停在 Scripted single-cycle 不稳定点；7/30 天及真实 Codex decision/action/multi-cycle 均 NOT RUN。只读收尾确认 **GER / 1936-03-26 04:00 / paused**；10 个已有存档和 Mod 选择文件哈希不变：[final-state.json](artifacts/phase5/runtime-20261006/final-state.json)。两次正常 GUI fresh bootstrap 单独记录，非 autonomous benchmark 游戏日。真实 Codex provider 尚未接入；Phase 5 不宣称 COMPLETE 或 Computer Use 已对整个 Phase 5 Runtime 可选。没有 commit/push。下一步须先只读核实生产数字 reader 与已提交动作，不能直接重跑 setter。

## Seven-action gate 验收历史

**Phase 5：NATIVE SEVEN-ACTION GATE 7/7 CONFIRMED / WAITING FOR NEXT INSTRUCTION。** 当前 Germany 1936 测试局面的 Research、National Focus、Production factory count、Construction、Army assignment、Frontline、Offensive Line 全部以正常 GUI 完成一次 mutation 和确定性重复读回。每项成功先落盘；Computer Use pump 全程 **OFF**。

七项均为 native GDI BitBlt / physical 2560×1600、DPI120；输入为 SendInput，Army 使用一次 right click、Offensive 使用一次 right_drag，其余 mutation 为 left click。五项原调用 uncertain 后重新观察并做只读确认，没有重发；另有一次必要 Army 创建准备。逐项 confirmed、native capture/input primitive、duration 和 readback source 见 [Phase 5 报告](PHASE5_AGENT_RUNTIME.md) 与 [gate-summary.json](artifacts/phase5/gate-20261006/gate-summary.json)。

| Action | Gate | Native capture | Native input primitive | 原调用 ms / 后续确认 ms | Readback source | Pump |
|---|---|---|---|---|---|---|
| Research | confirmed | GDI physical | SendInput left click | 5531 / 0 | GUI slot + fresh v2 researching | OFF |
| National Focus | confirmed | GDI physical | SendInput left click | 3782 / 0 | GUI active/cancel + fresh v2 progress | OFF |
| Production | confirmed | GDI physical | SendInput left click | 7391 / 11563 | GUI 数字 AND 格子 AND 总数；重复 | OFF |
| Construction | confirmed | GDI physical | SendInput state click | 8594 / 1844 | GUI 完整队列/州/建筑/数量；重复 | OFF |
| Army | confirmed | GDI physical | SendInput right click | 14109 / 13140 | GUI 精确成员/无将领/第三师未分配；重复 | OFF |
| Frontline | confirmed | GDI physical | SendInput border click | 17672 / 23109 | GUI 三边界段 + 全视口 mask + Army/plan；重复 | OFF |
| Offensive Line | confirmed | GDI physical | SendInput right_drag | 17641 / 13469 | GUI Army/front + 起点/尖端/目标/标签 + 全视口 mask；重复 | OFF |

最终完整回归 **389 passed / 10 subtests passed**；compileall、pip check、diff check 通过。首次旧 loopback WinError 10053 已精准复测及完整复测通过，原失败日志保留。[验证证据](artifacts/phase5/gate-20261006/verification.json)。

结束 **GER / 1936-03-24 05:00 / paused**，保留测试前线/进攻线，计划停止。没有 console/effect/memory write/save edit、Mod 选择变更、人工保存/覆盖或读档。10 个已有存档及 Mod 选择文件哈希全部一致：[最终文件复核](artifacts/phase5/gate-20261006/final/files.json)。本轮没有 commit/push。

验收限定当前 physical profile、固定 camera 和已校准目标。其他 native domain/camera/resolution 未验收，军事 telemetry 仍 UNKNOWN，不宣称 Computer Use 已完全可选。**AgentRuntime、其他 AI 和 autonomous benchmark 均未开始；按用户要求停止，等待下一步。**

## Phase 4 验收历史

**Phase 4 — Military Control：COMPLETE / OFFLINE TESTED / LIMITED LIVE VERIFIED。** 唯一剩余 completion gate `create_offensive_line ×2 confirmed` 已完成，完整回归通过。本轮停止于 Phase 4，未进入 Phase 5。报告：[PHASE4_MILITARY_CONTROL.md](PHASE4_MILITARY_CONTROL.md)，架构：[ARCHITECTURE.md](ARCHITECTURE.md)。

2026-10-05 后续 Git 交付按操作者明确的提交 / push 请求执行。验收 JSON 中 staged / committed / pushed 为当时快照，保留原始记录；交付状态以 Git 提交及远端同步结果为准。

新增独立 `GER_1936_2048x1280` MapProfile：UI scale 1.0 / land，使用真实截图校准 Amsterdam、Copenhagen、Königsberg 三处锚点。按实际 capture 的精确宽高选择 profile，再验证锚点和地图模式；任意分辨率、camera 漂移或坏锚点拒绝，没有缩放旧坐标。原 `GER_1936_2560x1080` profile 与既有 Army / Front / Plan / Supply / Air / Navy 证据保留；新 profile 只增加进攻线需要的选中 Army / Front / Order 观察，不迁移其他动作。

两个独立官方 SDK stdio 会话通过未变的 `create_offensive_line(army_id, target)`：`GER_POL_mainland_Poznan_east` 和 `GER_POL_mainland_Poland_north_east` 各 **confirmed ×1 / 5938 ms**。各自从无进攻线开始，fresh telemetry、Army/Front session 身份、三锚点、工具激活检查后，原生右拖只提交一次，右键释放成功，专用 reader 两次确认相同军队、相同前线、预期方向及校准视口无额外订单；retry 均为 0。订单使用 GUI_ONLY / session-local ID / version / 120 秒 TTL / signature。实机军事 telemetry 仍 UNKNOWN。证据：[本轮汇总](artifacts/phase4/offensive2048/live-summary-20261005.json)、[波兹南以东 SDK](artifacts/phase4/offensive2048/sdk-poz-attempt3.json)、[波兰东北 SDK](artifacts/phase4/offensive2048/sdk-north-east-result.json)。

保留人工校准的失败、东普鲁士方向关联到本土前线的错误样本，以及两次只调用 get_fronts 的提交前 SDK timeout；不计为成功，不自动重发。东普鲁士进攻线不启用，本轮按已授权范围使用两个不同的本土 semantic target。独立释放监视、F12、失焦、deadline、watchdog、鼠标 ownership、finally release 与 action lock 保留；异常释放场景的证明来自既有 26 项离线测试，未重做实机故障注入。

本轮完整回归 **295 passed / 10 subtests passed**，在 263 项基线上新增 32 项 profile / 专用进攻线 reader / 单次提交 / 重复回读 / 不确定失效测试；compileall、pip check、文档链接和 diff 检查见 [verification.json](artifacts/phase4/offensive2048/verification.json)。受限环境 pytest Temp 访问被拒绝，使用仓库内新的 `--basetemp` 完成同一完整测试集，未改测试收集或放宽断言。

结束时游戏仍打开，真实 GUI 确认 **1936-01-26 08:00 / paused**，保留第二条验收进攻线和选中集团军，没有执行计划。本轮未保存、读档、重启或修改显示设置；10 个存档及 Mod 选择文件 SHA256 均与基线一致，无新增存档，见 [最终哈希](artifacts/phase4/offensive2048/final-files.json) 和 [结束截图](artifacts/phase4/offensive2048/captures/final-paused.jpg)。SDK 已退出。第二次结果落盘后，额外桥接启动被自动审批以可能重复提交为由拒绝；没有绕过或重复提交，直接读取成功证据并正常暂停。

2026-10-02 的 25 个 SDK 会话 / 74 次调用 / 47 confirmed 历史汇总保留：[历史实机汇总](artifacts/phase4/live-summary-20261002.json)。原 Army、师分配/移除、将领、两处 frontline、Plan 开关、单师 Supply、有限 Air 和 Navy 观察未重验。本轮两个成功会话额外确认 get_fronts ×2 和 offensive line ×2。2026-10-04 的 263 项回归及 profile 不匹配拒绝保留：[原语与显示诊断](artifacts/phase4/offensive/live-summary-20261004.json)。完整游戏对象 ID、通用 province resolver、任意 Air/Navy/分辨率/camera 继续 UNKNOWN / PARTIAL / unsupported；`move_divisions` 和 Navy mutation 明确拒绝，均不新增完成门槛。

## Phase 3 验收历史

**Phase 3 — Non-Military GUI Executor：COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 PoC）。** Production 剩余动作、Construction、Laws、Advisors、Trade 达到该轮限定标准，该轮停止于 Phase 3；已提交 `2b1e1f3`。报告：[PHASE3_NON_MILITARY_EXECUTOR.md](PHASE3_NON_MILITARY_EXECUTOR.md)。

vendor-neutral contract / Python facade / InputBackend / guarded transaction 已落实。官方 SDK stdio → 正常 GUI → 重复 readback confirmed：Production create ×2 / reorder ×2 / delete ×2；Construction 三州三建筑 build ×3 / cancel ×6 / priority ×2；经济法 ×2 / 征兵法 ×2（含恢复）；沙赫特 hire ×1；SWE steel import ×4（含归零恢复）及独立 Trade getter ×1。提交 retry 均为 0。原 Research / Focus / factory assignment 的既有 live 证据保留，没有重测。

最终离线 **194 passed / 10 subtests passed**；compileall、pip check、模板重建和 git diff --check 通过。统一结果区分六种状态；snapshot 使用 session/version/TTL/signature，未知身份拒绝操作，提交后不自动重试。GUI 派生生产、建筑、顾问和贸易证据单独标注，不冒称逐线 telemetry。平均延迟、10 条原始失败和恢复记录见 [实机汇总](artifacts/phase3/live-summary-20261002.json)。

测试后通过正常 GUI 恢复生产、建筑、法律和贸易，再正常读取 `GER_1936_01_01_12.hoi4`，第一次恢复已确认 **1936-01-01 12:00 / paused**、顾问三槽为空、建筑队列为空。独立 Trade getter 需短暂正常推进到 1936 年 1 月 2–3 日取得 fresh telemetry；之后再次提交正常读档。收尾时游戏窗口已最小化，不自动拉前台，因此第二次加载结束的 GUI 状态未复核；[恢复记录](artifacts/phase3/restoration.json)明确区分已验证状态和最终 UNKNOWN。8 个原存档（含 autosave）及 Mod 选择 SHA256 仍与基线一致。当前 chat 新 action 注册 UNKNOWN，官方 SDK 的 25 个 MCP tools 已验证；Phase 3 提交包含实现、测试、文档与验证证据，运行时凭据、存档备份和临时测试目录不纳入 Git。

操作者明确允许直接 Computer Use 和正常 GUI 自动解除暂停/启动游戏；不自动拉前台，不修改 Mod 选择，不使用 cheat/effect/save mutation。当前实測 base Chinese / Telemetry Mod only / 2560×1080 / scale 1.0。测试从 GER 1936 开局自然推进到 1937，时间变化单独记录，不冒称全部 live 位于 1936。

**历史 Phase 3B-1：CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 Production GUI Executor PoC）。** `get_production_lines()` 与 `set_production_factory_count()` 既有验收见 [PHASE3B1_PRODUCTION_EXECUTOR.md](PHASE3B1_PRODUCTION_EXECUTOR.md)。

Phase 3A 保持 **CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED**；Research 和 National Focus GUI action 各 3 次 confirmed，既有安全 guard 实机证据保留，本轮没有重演。报告：[PHASE3A_GUI_EXECUTOR.md](PHASE3A_GUI_EXECUTOR.md)。

Phase 2B 保持 **COMPLETE / OFFLINE TESTED / LIVE VERIFIED / CODEX CHAT VERIFIED**；范围和既有证据见 [PHASE2B_EXTENDED_TELEMETRY.md](PHASE2B_EXTENDED_TELEMETRY.md)。

Phase 2A 保持 **CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED (GERMANY 1936 + SAVE/LOAD)**；证据见 [PHASE2A_TELEMETRY_POC.md](PHASE2A_TELEMETRY_POC.md)。速度 1–5 完整对照及游戏画面日期到日志的精确延迟尚未测量。

## 已实现

- Phase 4：MCP v0.7.0 opt-in `--military` 与 `OperatorAPI.execute()`；军事 SessionSnapshots / 字段来源 / 一次提交和两次精确 readback，两个独立 MapProfile 和可重建模板。既有 Army / Front / Plan / Supply / Air / Navy 观察及新增两处进攻方向达到限定验收；Province movement 和两个 Navy mutation 拒绝，不进入 Phase 5。
- Phase 3：MCP v0.6.0 opt-in `--non-military` 与普通 `OperatorAPI.execute()`；两个装备 catalog、最多十条完整紧凑军工行、三州/三建筑单项队列、两组合法法律切换、有限德国顾问和 SWE steel 0–2 民工进口。公共接口不接受坐标、模板、HWND 或 Computer Use 对象；默认未连接 backend 时拒绝 GUI action。换装备、通用滚动/任意州、其他贸易目标、完整 Agent Adapter / native backend 保持未实现。
- Phase 3B-1：MCP v0.5.0 新增 Production getter / factory-count setter；GUI 临时 ID 的 session/version/TTL、行身份/顺序/数量重新验证、数字 AND 工厂格重复确认、fresh GER telemetry/MIL-total 交叉检查。只有顶部六条校准军工行及 0–15 工厂范围，截断名称两条只观察、拒绝调整；逐线 telemetry、内部 equipment ID、效率、产量继续 UNKNOWN。没有扩展 Telemetry Mod；原 safety/Computer Use pump/动作锁保留，提交 retry 0。
- Phase 3A：确定性 Research / Focus Executor、集中布局/模板、正常更换研究确认、F12/失焦/独立 watchdog/timeout/Esc recovery、最多一次提交前导航 retry。MCP 两个语义 action 保留，默认不连接 GUI；现有七个只读查询工具与注册配置保留。没有作弊/effect API、Army / Front / AI Planner。
- Phase 1：完成参考项目和本机 HOI4 1.19.3 的静态能力调查；没有重做该阶段。
- Phase 2A：独立只读 Mod 在德国玩家开局/每日输出带 version、seq 和起止标记的状态帧；Python 增量 tailer、完整帧 parser、结构化 GameState、带时间戳的 state cache 和本地 JSON 查询命令已写入。
- 解析器、日志轮转和状态缓存已覆盖坏帧、重复字段、孤立 END、半行、截断/重建与读档日期回退；无开局标记时通过两个向前的较小每日序号确认新时间线。
- `pytest.ini` 将默认收集限制到本项目 `tests`；`scripts/check_telemetry.py` 只读检查现有日志、完整帧、最新状态与缓存时效。
- Mod launcher descriptor 安装脚本和实机启动脚本已写入。Telemetry Mod 描述文件已安装到 HOI4 用户目录；本轮 Mod 选择由操作者在启动器手工切换，Codex 未修改。
- Phase 2B：MCP stdio v0.3.0 提供 `get_summary`、`get_politics`、`get_industry`、`get_research`、`get_focus`、`get_changes`、`get_diagnostics` 及 2 个资源。保留进程内 100 条变化，读档与日志重建显式重置时间线，支持 MCP 2026 资源更新通知；完整科研槽映射/剩余时间、当前国策 ID、逐线生产字段保持 UNKNOWN。
- 独立 `.venv` 已安装官方 MCP SDK 2.2.0；项目接入配置已准备，服务也已通过官方 CLI 注册并可用 `codex mcp get hoi4_telemetry --json` 查到。

## Phase 3B-1 验证与限制

最终离线 **124 passed / 10 subtests passed**；compileall、pip check、git diff --check 通过。真实 SDK A/B/C 均 confirmed，另一次恢复 confirmed，retry 均为 0。三项验收平均 total **8458.33 ms**（snapshot 21、navigation 2005、adjustment 4531、confirmation 1021 ms）。Session 1 stdio pipe 被 sandbox 拒绝、未进入 GUI；Session 2 首次增配后的 JPEG header/grid 识别不确定，正确停止、未重发；修复真实样本回归后 Session 3 成功。原始结果与失败记录见报告。

逐线计数确认明确来自 GUI，不冒称 telemetry 能读取逐线分配。固定 1.19.3 / GER 1936 / 中文 / 2560×1080 / scale 1.0；无 scrolling、生产线创建/删除/换装备/重排。第一、第二条已实机验证，第三/第六条标题截断拒绝 setter，第四/第五条 setter 尚未实机验证。现有 chat 七查询注册未改，新 Production tools 当前聊天注册 UNKNOWN，真实官方 SDK stdio 闭环已验证。Computer Use pump 仍是 PoC 技术债，没有并行重写 native worker。

正常 GUI 恢复原可见工厂配置 `[10,2,1,2,2,1]` 和 20/28，再通过正常菜单读回原手动存档，当前暂停在 **1936-01-22 11:00**。真实截图经同一 reader 核对；测试期间自然运行覆盖 autosave，没有直接修改 save 或 Mod 选择。Mod 选择 SHA256 前后一致。恢复后未推进新日帧，较晚日志不能当作恢复后的实时状态。证据：[Phase 3B-1 汇总](artifacts/phase3b1/live-summary-20261001.json)。

## Phase 3A 验证与限制（历史）

最终离线 **79 passed / 10 subtests passed**；compileall、pip check、git diff --check 通过。真实 SDK 六次动作均 confirmed，自动 retry 0；Research 平均 13979.67 ms，Focus 平均 8172 ms。bridge 初始启动时序与 JPEG 格式失败已修复，Research 因此人工重发 2 次；另验证 stale 拒绝与无 pump 的 timeout。独立 Windows guard 实测 F12、失焦和停滞 watchdog 成功；故障状态机、重试、already_satisfied 和联合确认由离线测试覆盖。

固定本机实测 2560×1080 / UI scale 1.0 / GER 1936 / 中文 / 原有 Mod 组合；三项跟踪科技和莱茵兰国策为 allowlist。telemetry active focus ID、完整槽映射仍 UNKNOWN，GUI 身份证据独立注明。Executor 依赖 Computer Use 会话中的 pump，尚不是独立原生桌面服务；当前聊天新增 action 注册未验证，真实 stdio SDK action 已验证。

原存档预先备份，本轮正常 GUI 保存原局面为 GER_1936_01_22_11.hoi4；重复验证使用正常更换研究、Cancel/Start 和读档。运行中自然推进到 4 月并覆盖 autosave，原 autosave 备份保留；两份原手动存档 SHA256 不变。收尾已正常读档恢复到 1936-01-22 11:00 并暂停，GUI 核对原研究/国策，Mod 选择 SHA256 前后一致。恢复后未推进新日帧，日志缓存的较晚时间线不能当作恢复后的实时状态。详见 [实机汇总](artifacts/phase3a/live-summary-20261001.json)。

## Phase 2 验收历史

本机 HOI4 1.19.3 生成文档及参考项目的日志写法已静态核对。`python -m pytest -q` **15 passed**；`--collect-only` 只列出本项目测试，没有扫描参考项目；Python 语法检查和模拟日志 JSON 查询通过。2026-09-30 操作者手工仅启用 Telemetry Mod，进入 Germany 1936：真实 `game.log` 有 15 组完整帧，解析错误和 Telemetry 相关游戏错误均为 0；seq 随游戏日从 706640 增至 706650，读回较早存档后回退至 706645，并在第二个较小且向前的每日帧恢复缓存。暂停超过 30 秒显示 `stale`。日志平均 393 字节/帧；监听进程暂停时 10 秒 CPU 增量为 0。详情及未测项见 Phase 2A 报告。

## Phase 2 后续验收记录（历史）

Phase 2B 新增 6 项变化/时效测试、4 项 MCP 协议测试及 2 项持续监听测试，虚拟环境中默认 pytest **27 passed**；语法检查通过，依赖未改变且此前一致性检查通过。2026-09-30 21:47–21:54，操作者手工启动和推进游戏：同一真实 stdio MCP 会话收到 14 次资源通知，记录 9 次状态更新、1 次日志重建和 1 次读档 timeline reset；暂停产生 3 次 stale 通知。GER 日期从 1 月 6 日推进到 13 日，读档后缓存在第二个较小且向前的帧接受 1 月 7 日/seq 706646，随后正常更新到 8 日/706647。全程 parser/read 错误为 0。完整记录与统计见 Phase 2B 报告；游戏画面数值逐项对照未做。

当前宿主重启后，原有五个工具已实际调用成功，原接入阻塞解除；新 v2 服务已经实机验证；两个新增工具的当前聊天调用已在再次重启后通过。全局 MCP 注册前后的一致性比较未通过，且注册前完整快照未保存，其他配置是否被官方 CLI 规范化尚未确认；本轮没有修改全局配置，详情见 Phase 2B 报告。

继续实机检查：两分钟监听再收到 4 次状态更新及 1 次 stale 通知，最新 GER 为 1 月 12 日/seq 706651，parser/read 错误为 0。Codex 0.151.0 app-server 已发现 5 个工具，并实际读取两个 MCP 资源；证据见 [phase2b-codex-host-check.json](phase2b-codex-host-check.json)。宿主重启后的实际聊天工具调用证据见 [phase2b-codex-chat-v1-verified.json](phase2b-codex-chat-v1-verified.json)。

2026-10-01：protocol v2 的科研/国策扩展通过 Computer Use 实机验收，游戏条件为 HOI4 1.19.3、Germany 1936、Telemetry 加两个汉化 Mod。科研界面 4 槽，三项科技研究中和完成状态均核对；日志记录全部十个未完成进度区间及国策完成 [1,1]。原始日志 266 个完整帧、parser 错误 0、Telemetry 相关游戏错误 0。正式 SDK stdio 的七个工具实际查询成功；当前国策 ID 等未证实项继续 UNKNOWN。

分两次持续监听：正常推进会话 204 次通知、202 次 state_updated、暂停 stale；读档验证会话先读取旧 seq 706883，再接受回退后第二个每日帧 seq 706641，记录 1 次 timeline_reset 和后续 9 次正常更新，科研与国策完成标志恢复到未完成。两个会话 parser/read 错误均为 0。最终游戏暂停在 1 月 22 日 11:00，最近日帧 seq 706660、暂停查询 stale。证据汇总：[phase2b-v2-live-summary-20261001.json](phase2b-v2-live-summary-20261001.json)。

收尾复测 **33 passed / 10 subtests passed**；compileall、git diff --check 和文档链接检查通过。已将能力资源的新字段实机验证声明更新为 true（限本轮测试条件）。两次监听客户端均已正常退出。

新建测试存档 GER_1936_01_01_12.hoi4；原手动存档 GER_1936_01_06_23.hoi4 仍在。正常推进期间游戏自动存档覆盖原 autosave（1942 年存档），没有预先备份，当前存档目录无备份文件。未修改 Mod 选择。

2026-10-01 宿主重启后的最终接入验收：当前聊天发现并实际调用全部七个工具，均成功；get_summary 确认 protocol v2 / GER / seq 706660 / 1 月 21 日 24:00，get_research 返回 4 槽及三项研究中，get_focus 返回莱茵兰未完成及 [0.6,0.7]；get_diagnostics 的 parser_errors=[]、log_read_error=null。结果与已归档实机状态一致。暂停日志 stale 正常，基线 freshness_basis=log_mtime_upper_bound、revision=0 属于重启回放；本次查询不额外证明实时新帧通知。证据：[phase2b-codex-chat-v2-verified.json](phase2b-codex-chat-v2-verified.json)。

Phase 2B 本轮限定范围已完成，无剩余接入阻塞。完整科研槽映射/剩余时间、当前国策 ID、逐线生产保持 UNKNOWN；逐档速度/精确延迟及早先全局配置一致性未确认项仍保留。尚未进入产品 GUI Executor、军队/生产操作阶段。本次仅查询和更新验收记录，没有游戏操作或配置修改。
