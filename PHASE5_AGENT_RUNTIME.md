# Phase 5 — Independent Native Backend and Pluggable Agent Runtime

## 2026-10-09 提交 checkpoint

状态 **IN PROGRESS**。最新六态 stop-only Matrix 已离线验证；本次提交前完整回归 **604 passed / 10 subtests passed，82.95s**：[日志](artifacts/phase5/commit-20261009/pytest-full-1.txt)；compileall、pip check 通过。保留 legacy modal 分类，增加独立 `stop_state` 与不可执行的 `candidate_stop_route`；只有 live proof / PNG 哈希 / profile / 双次菜单暂停 / modal identity 不变全部符合，才能加载新 `escape_to_menu` 路径。当前没有 World News live proof，因此没有启用该路径，也没有重跑实机 gate。

历史 seven-action 7/7、Scripted factory mutation、Construction mutation、有限7天和 Time Safety A/B 保留；历史失败仍为失败。真实 Codex、非 Codex 模型、新30天和180天均待验收，不能用 fake provider 或离线通过补齐。新的执行规则及顺序见 [STATUS.md](STATUS.md) 与 [当前执行 checkpoint](artifacts/phase5/final-execution-20261007/CHECKPOINT.md)。本次提交准备不进行游戏输入，pump OFF；以下内容为历史验收记录。

## 2026-10-07 时间安全修复与新实机验收

状态：**IN PROGRESS / TIME SAFETY A+B CONFIRMED / CONSTRUCTION SINGLE CONFIRMED / NEW 30-DAY FAILED**。本轮新增 time ownership / bounded safe stop / private exact-failure evidence，保持原 Scripted target=Kar98k 12、原 action priorities、GUI 阈值、calibrated targets 和五阶段结构。历史21/30及tool-20261007不改写。

| Gate | 实际结果 | 证据 / run |
|---|---|---|
| Time Safety A | 实机 PASSED；resume→fresh telemetry→normal pause confirmed→release，advance 7563 ms；acquired/released 1/1 | `live-A-1/result.json`；6a53a661-2d13-4abc-b963-c3009f87bb44 |
| Time Safety B | 实机 PASSED；实际已校准菜单阻挡 normal pause，STOP_FAILED_OWNED 保留责任，再双次菜单暂停读回 release；pause fail1、safe stop success1；无恢复重发 | `live-B-1/result.json`；056ddff4-1d7c-4b12-b436-66c54379187a |
| Time Safety C | 仅离线 PASSED；失焦/F12/timeout/input/evidence/cleanup/circuit等失败不丢ownership、不重发；未在实机故意制造失控 | 31项新增 `tests/test_time_safety.py`；完整585/10 |
| 新 baseline | 实机 PASSED；GUI paused、NO_MODAL、fresh/frame_received_at；独立测试准备，不计Agent行为/benchmark | `live-baseline-1/result.json`；08664687-1c60-40e2-9797-785247cb7dc8 |
| 新 Construction single | **SINGLE_CYCLE_CONFIRMED**；3 observations / 1 decision / 1 action / 1 confirmed mutation，fresh post observation通过；wall56.344s | `construction-single-1/assessment.json`；577347d0-3ff3-4f0f-b4c4-c7a5ab5eb198 |
| 新30天 | **BLOCKED / FAILED**；7 confirmed推进日，fresh日期差8日；12 observations / 2 valid no-op / 0 actions；wall96.485s | `scripted-days30-1/assessment.json`；c6d10d44-d4f7-4916-8475-e08f81041d35 |
| 真实Codex / 3–5cycles | **NOT RUN**；前一gate失败后停止，真实模型调用0，fake历史测试不算真实推理 | 未接provider或其他模型 |

全部实机 capture 为 native GDI BitBlt physical RGB，input 为 SendInput，2560×1600/DPI120，Computer Use pump OFF。每个 gate 的 result / summary 均先落盘再进入下一项；无 Codex/操作者代替 Scripted 决定战略动作。

### 单轮 Construction 证据

全新 Host / telemetry session / Runtime / Observation / Catalog；Scripted自主提出 `build(state_id=64,building_type=civilian_factory,count=1)`。action **4db28f33-5a5f-4a3f-86eb-324bbeadc43e**：confirmed、mutation_submitted=true、duration13094ms、retry_count=0。正常GUI工具/州单次提交，完整queue的州/建筑/数量重复确定性读回；fresh后置四域观察与navigation通过。shutdown clean_no_owned_time / game_pause=true，acquired/released2/2。启动及post fresh bootstrap各自审计，game_days=0，不把日期推进算benchmark或战略行为。

### 新30天失败与真实安全状态

1936-08-08→1936-08-16日期差8天；Runtime仅计7个 confirmed时间步骤。第8次推进拿到fresh telemetry后遇到实际“第11届奥林匹克运动会”World News。normal pause 在输入前被 modal_blocked 拒绝；KNOWN_BLOCKING_MODAL / world_news / stop_route=null，不发送未验证的Escape、也不自动确认新闻按钮。独立safe stop有界尝试失败，后续停止调用只读观察，未重发输入。

新状态机不再丢停止责任：time_ownership_acquired=9 / released=8，pause_attempts=9 / failures=1，safe_stop_attempts=1 / successes=0；modal_block_count=4是重复观察/失败分支次数，不是四个独立弹窗。unknown_modal_count=0，circuit_breaker=time_stop_failed，最终STOP_FAILED_OWNED / owns_running=true；**shutdown=unsafe_stop_failed、game_pause=UNKNOWN、operator_intervention_required=true**。这证明失败责任和报告修复已生效，也暴露安全停机覆盖仍不足，不能宣称长周期无人值守。

原始run记录human_strategic_interventions=0、operator_safety_interventions=0指退出前计数；退出后已单独请求人工安全暂停。人工接管不能改写原run为零介入成功，也不能把当前只读Host的owns_running=false当作旧ownership自动释放。

精确暂停/恢复失败帧、clock/modal/menu ROI、UTC、telemetry、foreground、HWND589988/PID16820已在恢复前保存；5份time-failure私有JSON/PNG保留。trigger proof必须与later收尾帧分开。`final-readonly-1` 0输入仍见新闻modal、暂停UNKNOWN；日志last-known到1937-01-11，freshness_basis=log_mtime_upper_bound，不计benchmark或替代GUI日期/暂停。游戏仍可能走时，人工暂停请求待确认。

策略覆盖仍有限：两次决策均合法空actions，建造队列在两次可靠战略观察中非空，Kar98k保持12。research/focus idle各为2个known dates的2次idle观察，queue idle0/2；unused MIL known4/unused4/unknown8。连续空闲小时/天数UNKNOWN，不能推作全程。native map审计MAP_READY17 / MAP_UNRESOLVED2，0recovery，0clock recovery；无重复建设、人工战略干预或snapshot/timeline错误，不意味着策略完整。

### 验证与下一步

完整 **585 passed /10 subtests，75.34s**：[pytest-full-2.txt](artifacts/phase5/time-safety-20261007/pytest-full-2.txt)。相关104 passed包含73 Runtime旧测试+31新增time-safety；compileall通过。新增测试覆盖ownership保留、Space/Escape预算、真实modal fixtures、精确RGB/ROI、guard不可捕获、输入异常旧帧失效、证据写盘错误、shutdown/circuit报告。它们不替代真实provider或所有modal实机测试。

原9手动存档、autosave及Mod文件哈希保持，无新增/删除；未commit/push、使用console/effect/memory/save编辑、接其他模型或扩大GUI范围。按本轮附件“任一gate失败即停止”，本checkpoint不继续修新闻route或重跑gate。剩余顺序：人工暂停确认→已知World News stop-only校准/验收→新fresh baseline→新30天→真实Codex single→3–5cycles。旧Construction confirmed保留，不无意义重造队列。

国家自治后续计划见 [COUNTRY_AUTONOMY_PLAN.md](COUNTRY_AUTONOMY_PLAN.md)。先建立德国1936和平期180天有持续科研/国策/建设/生产决策的可玩版本，可靠停止及常见事件覆盖是前置条件；之后才扩展陆战、空海军及其他国家。本轮只规划，Phase 5仍未COMPLETE。

证据目录：[Time Safety](artifacts/phase5/time-safety-20261007/TIME_SAFETY_GATE.md)、[Construction](artifacts/phase5/time-safety-20261007/construction-single-1/summary.json)、[30天原始事件](artifacts/phase5/time-safety-20261007/scripted-days30-1/events.jsonl)、[30天assessment](artifacts/phase5/time-safety-20261007/scripted-days30-1/assessment.json)、[当前只读收尾](artifacts/phase5/time-safety-20261007/final-readonly-1/final-state.json)。

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

## 2026-10-07 地图和Clock修复checkpoint

**Phase 5：IN PROGRESS / MAP AND CLOCK REPAIR OFFLINE TESTED / CONSTRUCTION REVALIDATION FAILED。** 尚未达到“能用”。原seven-action 7/7、新Scripted工厂单轮confirmed和7天有限稳定性保留；原30天第21日失败不改写。本轮新的Construction单轮在提交前返回rejected / requirements_not_met，mutation_submitted=false、retry0；按用户附件“若任一关键验收失败，停在当前安全checkpoint”停止。新30天、真实Codex及multi-cycle均NOT RUN。


| 本轮项目 | 实际结果 |
|---|---|
| 原MapResolver失败分类 | **camera drift**：旧准备/single/7/30的preflight已经失配；Copenhagen/Warsaw实际位置改变，land mode及physical geometry正常。Construction开关不移动camera；最初谁触发平移/缩放仍UNKNOWN |
| 地图状态管理 | 新NativeMapState区分MAP_READY / MAP_RECOVERABLE / MAP_UNRESOLVED；保留原gate camera，并限定四份实机fixture覆盖的Germany首都camera范围。一次有界、guard内Find View→Go to Capital→固定wheel导航后重验三锚点；不能恢复则拒绝，无任意province/坐标缩放 |
| Catalog / Executor | 明确semantic implementation、backend、profile calibration、map readiness和target identity；不可解析目标temporarily_blocked。独立state64/GER身份后仍在提交前重验。当前工具确认尚未通过完整实机流程，catalog预检不保证提交成功 |
| Construction模式校准 | 标签在civilian overlay中隐藏，HUD模式改变；以正向工具/模式识别和至少100个独立特征、90%一像素一致、三分区及state64区域各>=10匹配验证未移动，不计算目标transform。drawing4只读实机：258/278、92.8%、state64区域12，空队列、paused、0 mutation |
| Construction新单轮 | **FAILED**，run d458ccbd-6546-4233-9295-1bcd6c2b388a；1936-04-30、wall29.297s；3观察、1决策、1attempt、0confirmed / 1rejected / 0uncertain / 0timeout；PLAN_STOPPED |
| 动作明细 | build(state64,civilian_factory,1)，45fa0ad4-0f67-480d-a5ca-59214ec071e4；**rejected / requirements_not_met / 7968ms**；mutation_submitted=false、retry0。GDI capture，SendInput仅导航/工具选择；真正build点击及mutation readback未进入，readback/confirmation=0ms |
| 当前blocker及证据缺口 | 真实Executor的civilian selected-tool图标未得到匹配，停在最终地图检查和commit之前。具体动画/toggle原因仍UNKNOWN。本次没有保存精确工具失败RGB；新增帧落盘只覆盖地图拒绝，不能把之后的截图冒充失败帧。下一步需先补工具阶段帧及实际状态证据，再评估，不自动重发 |
| Clock | 菜单压暗导致旧header MAE39.8>8；先识别modal再检查header，菜单不能resume。空clock glyph也拒绝resume；known-menu pause独立于日期。实机fresh bootstrap7516ms confirmed/paused；收尾validated GUI glyph stability paused。GUI解码日期仍UNKNOWN；1936-04-30来自run内fresh telemetry，未混称GUI日期 |
| 新30天 | **NOT RUN**：Construction关键gate失败后停止。原21/30 failed run保持不动；没有只凭日期宣称稳定或战略自主 |
| Codex真实provider / action / multi-cycle | **全部NOT RUN，实际模型调用0**；前置Construction/30天gate未通过。历史CLI/登录只读readiness与fake callback不算真实模型。没有新增provider或接其他AI |

完整531 passed /10 subtests，46.82s，原493保持；最终两个小修正（recovery标志初始化、profile calibration与map临时状态分离）后的相关111 passed，8.63s。最终全量复核见pytest-final2.txt；前一次权限失败日志保持原样。默认沙箱临时目录WinError5失败单独保留，本机回归通过，不将其混作游戏证明。AgentRuntime/Scripted策略未修改；Kar98k目标仍12，native getter观察仍12。原single uncertain、later readback、single confirmed、7天与21天原始结果均保留。

当前报告：[本轮验证](artifacts/phase5/stability-20261007/verification.json)、[Construction run](artifacts/phase5/stability-20261007/construction-single-1/summary.json)、[事件和Operator proof](artifacts/phase5/stability-20261007/construction-single-1/events.jsonl)、[只读收尾](artifacts/phase5/stability-20261007/final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。

最终完整复核 **531 passed /10 subtests，46.85s**：[pytest-final2.txt](artifacts/phase5/stability-20261007/pytest-final2.txt)。前一次收尾复核有1项summary.tmp替换WinError5（530 passed）；原日志保留，相同失败组4/4及随后全量均通过，暂时权限/占用错误的根因仍UNKNOWN，未修改Runtime策略。

## 前一轮checkpoint（保留历史）

更新日期：2026-10-07。状态：**IN PROGRESS / SCRIPTED SINGLE MUTATION CONFIRMED / 7-DAY RUNTIME STABILITY CONFIRMED WITH LIMITED STRATEGY COVERAGE / 30-DAY STOPPED AT DAY 21**。原native seven-action gate保持7/7 confirmed，未重跑；真实Codex未进入。

## 本轮实机验收与停止点

用户明确保留Kar98k目标12，并单独授权操作者测试准备12→11。准备使用新snapshot、同一已校准装备/位置、一次OperatorAPI setter及独立getter：两者confirmed，数字/15-cell grid/global assigned MIL由22/28变21/28，其他七行不变。setter `b3b41eba-01c5-4b56-8422-64aba604c503`、12672ms；独立读回5734ms；wall36.953s；retry0、最终暂停。记录role=operator_test_preparation、counts_toward_agent_behavior=false，不计Agent动作/confirmed/benchmark日数。[方案和授权后结果](artifacts/phase5/continuation-20261007/TEST_PREPARATION.md)、[原setter](artifacts/phase5/continuation-20261007/test-preparation-1/setter.json)、[独立getter](artifacts/phase5/continuation-20261007/test-preparation-1/independent_readback.json)。原reader-20261006 uncertain/later_readback及seven-action历史保持不动。

随后启动全新Scripted session，保持原priority/目标规则和Runtime failure policy。Agent自主选择11→12；action `9d7e210f-28b3-407c-8072-25acf6c25b76`、duration **13391ms**、mutation_submitted=true、retry0、deterministic confirmed；目标数字/grid/全列表global22/28重复一致。正常GUI post-action fresh bootstrap单独记录，fresh四域后置观察全部通过，single gate **SINGLE_CYCLE_CONFIRMED**。

| Run | run_id | 游戏日期 | wall s | observations / decisions | actions / confirmed / rejected / uncertain / timed_out | 实际benchmark days | 结论 |
|---|---|---|---|---|---|---|---|
| Scripted single | a267d0f1-4d8e-44a3-b18b-5d72bbf01df0 | 1936-03-29→03-30 | 51.328 | 3 / 1 | 1 / 1 / 0 / 0 / 0 | 0 | mutation gate confirmed；日期差是单独fresh bootstrap |
| Scripted 7 days | b9e4a657-129b-48b6-b16a-6b0d61f321c0 | 1936-03-31→04-07 | 82.657 | 11 / 2 | 0 / 0 / 0 / 0 / 0 | 7 | Runtime稳定性通过；2次valid no-op，战略动作覆盖不足 |
| Scripted 30 days | 13b9f1f3-f1f6-4b8b-8803-477fd3679c69 | 1936-04-08→04-29 | 211.203 | 28 / 4 | 1 / 0 / 1 / 0 / 0 | 21 | PLAN_STOPPED，30天gate未通过；3次valid no-op及1次合法build提案 |

三个Run的already_satisfied/backend_errors/timeline_reset均为0，circuit_breaker=null；pump均OFF。7/30天各有单独启动fresh bootstrap一日，不计benchmark；实际benchmark日数按日期差验证。操作者只启动运行，没有中途选择战略动作、接管advance/execute或重复mutation。准备与benchmark分目录，所有原始结果落盘后才进行下一步。

7天通过不只依据日期：7次native时间推进均confirmed/paused、所有observation fresh、navigation confirmed、两次决策schema/catalog有效且与原Scripted规则一致；Kar98k在战略观察中重复读到12。[7天评估](artifacts/phase5/continuation-20261007/scripted-days7-1/assessment.json)。这轮全为valid no-op，**不宣称完整自主战略验收成功**；之后仅继续30天稳定性压力测试，不强迫Agent制造动作。

30天第21日，已完整观察到原建造队列为空，Agent自主选择state64/civilian_factory/count1。`325bff43-716c-480e-b753-ad14b1b59198`返回 **rejected / map_target_unresolved / 3000ms**，mutation_submitted=false、retry0。`ConstructionUI.change`先关闭建造页，再用`native_calibration.validate_map`要求三个城市锚点及land_mode匹配（均0.9阈值），失败发生在州点击和commit之前。不是输入提交成功，也不是uncertain；timings的submit字段包含验证步骤，不代表实际mutation。Runtime失效snapshot、summary重观察、quarantine该proposal、停止plan；未重发、未推进剩余9日，未触发熔断。原trace/事件保留：[30天summary](artifacts/phase5/continuation-20261007/scripted-days30-1/summary.json)、[事件/Operator proof](artifacts/phase5/continuation-20261007/scripted-days30-1/events.jsonl)、[失败评估](artifacts/phase5/continuation-20261007/scripted-days30-1/assessment.json)。

当前blocker是现有physical profile/state64的地图可解析性。原拒绝没有保存validate_map瞬间RGB，不能确定哪个锚点首先失败及视口变化的原因。只读收尾的截图已在Escape recovery打开的游戏菜单中，三个锚点不匹配、land_mode匹配；这**不是原提交前失败帧**，不用于猜州坐标或改模板。下一步先在既有范围补失败帧/视口证据并恢复校准可见性，不降低阈值、不扩大GUI、不自动重跑build。

idle只统计可靠采样日期：7天research/focus=2/2 known dates、construction queue=0/2，unused MIL=4 known/4 unused/7 unknown；30天research/focus=4/4、construction queue=1/4，unused MIL=6 known/6 unused/22 unknown。研究/国策/队列的连续24小时空闲时长仍UNKNOWN；不能把未观察日推作全程空闲。7/30天实际没有semantic mutation分别为7/21日，但30天有一次被拒绝的合法action attempt。分析只读取既有事件，不替Agent决策。

**真实Codex：NOT RUN，受前一30天gate失败阻断。** 只读核对确认本机Codex CLI 0.151.0已安装、ChatGPT登录成功，支持structured-output flag；官方 [Codex SDK](https://developers.openai.com/codex/sdk) 和 [app-server](https://learn.chatgpt.com/docs/app-server) 提供程序调用路径。本项目尚未完成满足Observation/Catalog/Goals/History输入隔离的真实provider验收；没有实际模型推理，也未安装SDK/接入其他模型。CLI存在和登录、生成本机协议schema不等于模型推理成功或semantic/native action通过；fake callback仍只是离线测试。[readiness.json](artifacts/phase5/continuation-20261007/codex-readiness.json)。

全程native GDI BitBlt / 2560×1600 physical / DPI120、SendInput（工厂增减left click、时间Space tap）；**pump OFF**。普通clock reader收尾返回clock_header_unrecognized，原UNKNOWN保留：[final-state.json](artifacts/phase5/continuation-20261007/final-state.json)。另用既有game-menu模板NCC=1.0/阈值0.9独立确认菜单暂停：[pause-menu-proof.json](artifacts/phase5/continuation-20261007/pause-menu-proof.json)；收尾零输入、未切换菜单。9个原手动存档及autosave/Mod哈希均不变，无新增/删除，无console/effect/save编辑、Mod变更、commit/push。

完整回归 **493 passed / 10 subtests passed，43.01s**，原483全部保持，新增10项独立准备的单次setter、异常停止、错误起始count/重复装备拒绝和独立读回冲突测试。Runtime/策略/reader/地图阈值未改；没有补故障绕行来跑满benchmark。[pytest](artifacts/phase5/continuation-20261007/pytest-full1.txt)、[验证汇总](artifacts/phase5/continuation-20261007/verification.json)。本轮停在30天gate，等待下一步。

## 2026-10-06 reader / single-cycle checkpoint（历史）

先只读确认已提交动作，再修 reader、全量回归、fresh single-cycle。没有重发上次 setter，没有改变 Runtime failure / quarantine / circuit policy 或 Scripted 策略。

只读实机确定 **Kar98k factories=12**：numeric=12 AND 15-cell grid=12 AND 完整八行合计=22、header=22/28；展开连续两帧一致，折叠后完整列表身份/顺序/数量重复一致。**original_status=uncertain，later_readback=12**；原 action `4d8accb9-2765-465c-be7a-86259134d317` 和历史 JSONL 未改写。证据：[readback.json](artifacts/phase5/reader-20261006/live-read-5/readback.json)。

| 本次只读确认 | 结果 |
|---|---|
| status / mutation_count | confirmed / 0 |
| native capture | GDI BitBlt，2560×1600 physical，DPI120 |
| native input | SendInput，仅打开/折叠/neutral 导航 |
| duration | 7500 ms |
| readback | numeric AND grid AND complete-list/global assigned MIL；重复一致 |
| CU pump / safe page | OFF / restored |

根因是 GDI 的 `22/28` 把第二个 `2` 和 `/` 连成16×13、57 foreground pixels 的组件；旧 header 只校准 joined `0/`，拒绝未知 `2/`。加入真实 `2/` 样本，与既有 `2`、`/` 掩码组合交叉核对 IoU=1.0。阈值保持 numeric/header最低分 **0.84**、胜者差 **0.10**、grid **0.85**；未引入 OCR / LLM reader。真实10/11/12 fixture来自原native gate和本次GDI capture。展开首帧曾出现grid渲染不完整；折叠后第二行也曾无法识别身份。现在折叠后使用既有neutral导航，并在guard内最多两秒被动捕获、要求连续两帧一致。等待内部没有click/key/submit retry；三个来源矛盾返回 `readback_ambiguous`，损坏glyph仍拒绝；失败记录保留。

Native getter 为当前runtime的 infantry_equipment_1 目标增加网格验证，结合全列表数字/global总数；其余行仅有numeric/global证据，保持partial。native setter提交前、每个单工厂step后及最终确认均要求目标三路一致。没有扩大catalog目标、分辨率或GUI domain。

最终全量 **483 passed / 10 subtests passed，41.41 s**，原452保持、新增31：[pytest-final.txt](artifacts/phase5/reader-20261006/pytest-final.txt)。其中480项回归已在fresh single之前通过；之后仅新增三项AA边缘像素跨分割阈值测试，再跑全量483通过。新增覆盖真实10/11/12、AA颜色及边缘扰动、1px偏移、非法glyph、numeric/grid/global冲突、展开/折叠异常帧、无输入有界等待、single confirmed/uncertain/no-op/失效后置观察、fake Codex同语义链与pump OFF、可靠idle审计。既有7-day scheduler/time/circuit/bounded history/no duplicate测试全部保留。新增审计测试初次遇到Windows GBK解码错误，改显式UTF-8后通过，没有放宽断言；compileall、pip check、diff check通过：[verification.json](artifacts/phase5/reader-20261006/verification.json)。

fresh single-cycle #2：[summary.json](artifacts/phase5/reader-20261006/scripted-single-2/summary.json)、[events.jsonl](artifacts/phase5/reader-20261006/scripted-single-2/events.jsonl)。run_id=`61d1ddc1-72db-4f20-8f0f-278941cb2679`；start/end=1936-03-27；wall=19.375s；observations=2、decisions=1；actions/results/confirmed/already_satisfied=0；rejected/uncertain/timed_out/backend_errors/timeline_reset=0；circuit_breaker=null；benchmark game_days=0。正常GUI fresh bootstrap单独推进一日后暂停，不计benchmark。四个strategic页面均native confirmed，Production getter **5860 ms**；使用新session/snapshot/catalog，未沿用旧identity。

当前catalog允许fresh 12→11，但原Scripted策略仅推荐上调；12已达到目录上界，recommended=null，Agent提出空actions。CLI新增严格single验收：必须有已提交且confirmed的mutation≥1、有效fresh post-action strategic observation、native backend/pump OFF；zero mutation、already_satisfied或uncertain+later readback不算成功。成功mutation之后的正常GUI fresh bootstrap/后置观察单独审计；本轮未进入该分支。

因此停在 **SINGLE_GATE_NOT_PASSED / confirmed_mutation_required**。已询问benchmark前固定维持11的策略选择，尚未收到回答，未自动改变规则或人工选择action。下一步先确定Scripted目标规则，再回归并跑fresh single；通过后才允许7→稳定后30→Codex semantic gate。7/30天及真实Codex均NOT RUN，未接入其他AI，未扩大Computer Use optional表述。

idle指标仅统计可靠idle观察的游戏日期，不推算连续24小时：research=1/1 known date、focus=1/1、construction queue=0/1；unused MIL=2 known/2 unused/0 unknown。[只读收尾](artifacts/phase5/reader-20261006/final-state.json)确认paused=true、pump OFF、收尾input_count=0；10个原存档及Mod选择哈希不变，无新增/删除。没有commit/push。

## 前一轮 Runtime checkpoint（历史）

用户的新授权继续统一 Phase 5：observation/catalog/runtime/scripted/Codex semantic adapter 和有限 autonomous 验证；不创建新 Phase 编号，不接其他 AI，不自动 commit/push。计划合理，先离线验证，再按规定顺序实机验收。

已实现 `ObservationAggregator`、`get_game_state(summary/strategic/detailed)`、`get_action_catalog`、`AgentAdapter / AgentDecision`、`AgentRuntime`、`ScriptedAgent`、`CodexAdapter(provider)` 和 `GameTimeController`。私有 `NativeRuntimeHost` 附加现有窗口，默认 WindowsNativeBackend / pump OFF；目录限制在当前 physical profile 和七类已校准语义目标，保留 TTL、freshness、身份检查、单次提交和 deterministic readback。数据缺口明确 unknown/partial/stale；GUI refresh 串行按需执行，不做每日全扫描。详细合同与限制见 [AGENT_API.md](AGENT_API.md)、[AGENT_RUNTIME.md](AGENT_RUNTIME.md)。

完整回归 **452 passed / 10 subtests passed，32.10 s**：原 389 项全部保留，新增 63 项覆盖 observation、catalog、decision schema、预算、failure/reobserve/quarantine、circuit breaker、timeline reset、Scripted 同接口调用、每日/每周调度、bounded history、结果持久化、time controller 和 fake Codex provider。compileall、pip check 通过：[verification.json](artifacts/phase5/runtime-20261006/verification.json)。第一轮回归的旧 MCP 清单未包含两个新增工具；已更新清单及 navigation annotation 预期后通过，没有放宽既有功能断言。未引入新的依赖或外部 review 流程。

| 实机步骤 | 结果 |
|---|---|
| Native foreground preflight | 初次 loss_of_focus；用户保持前台后通过；原始失败保留 |
| Strategic observation / catalog | confirmed；fresh 1936-03-25；四个页面串行读取并恢复安全页面；unknown domains 显式保留 |
| Scripted single-cycle | 不通过：一次 Production 11→12，uncertain / production_number_unreadable；停止计划，无重发 |
| Scripted 7 days / 30 days | NOT RUN |
| 真实 Codex decision / semantic action / limited multi-cycle | NOT RUN；仅 fake-provider adapter 测试完成 |

实机记录：[初次 preflight](artifacts/phase5/runtime-20261006/observation-1/summary.json)、[observation/catalog](artifacts/phase5/runtime-20261006/observation-2/summary.json)、[Scripted single summary](artifacts/phase5/runtime-20261006/scripted-single-1/summary.json)、[原始事件](artifacts/phase5/runtime-20261006/scripted-single-1/events.jsonl)。单轮 3 observations / 1 decision / 1 mutation / 1 uncertain / 0 rejected / 0 timeout；wall time 23.672 s，benchmark game days 0。没有 Codex 中途战略决策或人工选择 action。

Scripted → AgentRuntime → OperatorAPI → WindowsNativeBackend：原生 **GDI BitBlt / 2560×1600 physical / DPI120**；**SendInput left click** 提交一次，action ID `4d8accb9-2765-465c-be7a-86259134d317`，duration 7797 ms，retry 0，mutation_submitted=true。post-submit numeric reader 返回 production_number_unreadable，UI/telemetry deterministic confirmation 均未建立，after count 为 UNKNOWN。Runtime 正确停止计划、失效 snapshots、summary 重观察并隔离 proposal，原始 uncertain 不改写。native trace：[b398f0ba-b16c-44b5-ac2f-df2b69a33d0e.json](artifacts/phase5/runtime-20261006/scripted-single-1/native-audit/b398f0ba-b16c-44b5-ac2f-df2b69a33d0e.json)。不能将已存在 digit templates 或 catalog 的 available 等同于新计数 live readback 通过。

两次正常 GUI fresh bootstrap 均 resume → fresh date → pause confirmed，分别推进至 1936-03-25、1936-03-26；独立 20 秒 stop path、pump OFF。它们不是 7/30-day autonomous benchmark。只读最终 GDI capture 和校准 clock 确认 **1936-03-26 04:00 / paused**：[截图](artifacts/phase5/runtime-20261006/final-physical.png)、[final-state.json](artifacts/phase5/runtime-20261006/final-state.json)。10 个既有存档及 Mod 选择哈希不变，无新增/删除。没有 CU fallback、console/effect/memory write/save edit/Mod 修改或 commit/push。开始前 Git 状态：[git-status-before.txt](artifacts/phase5/runtime-20261006/git-status-before.txt)。

本轮停止在 Scripted single-cycle 的不稳定点。下一步必须先只读核实生产数字 reader 和已提交动作；不得直接重发 12 工厂 setter。修复/确认后才重新评估 single-cycle gate，再依序继续 7 → 稳定后 30 → 纯 semantic Codex decision/action → limited multi-cycle。真实 Codex provider 的工具隔离与 native action 仍需验收，不能将 fake-provider callback 视为实际接入。

当前允许的限定表述：**Computer Use is not required for the validated native runtime action subset.** Scripted 与 Codex Runtime 尚未实机通过，不能进一步宣称 Computer Use is optional for the validated Phase 5 runtime，更不能宣称整个项目已独立于 Computer Use。

## Seven-action gate 验收历史（此前完成）

原草案先验证独立 native backend，再实现 observation/catalog/runtime/adapter 的顺序合理；本轮严格停在七项 native gate。用户明确授权当前 Germany 1936 测试局面的具体 GUI mutation，以及有限正常时间推进取得 fresh telemetry。AgentRuntime、其他模型和 autonomous benchmark 均未实现或开始。

七项全部使用正常 HOI4 GUI、独立 official SDK stdio 和 WindowsNativeBackend。Computer Use pump 全程 **OFF**。没有 console、effect、memory write、直接修改 save、Mod 选择变更或人工保存/覆盖；没有执行作战计划。Codex 选择有限语义计划，未接入模型 client。

## 逐项实机验收

下表 GDI 指公开 Win32 **BitBlt → RGB、2560×1600 physical、DPI120**；输入均为 **SendInput.MOUSEINPUT**。`duration_ms` 为原 mutation API 调用 / 后续只读确认调用合计；不含 fresh 等待、前置 getter、先前失败尝试或工具审批等待。直接 confirmed 的原调用已包含重复读回。

| Action / 目标 | 最终 gate | native capture | native input primitive | duration_ms 原调用 / 后续确认 | readback source | CU pump |
|---|---|---|---|---|---|---|
| Research：slot 0 → basic_machine_tools | confirmed | GDI physical | left click / Start | 5531 / 0 | 槽身份和研究名称 GUI 重复读取 + fresh v2 researching predicate | OFF |
| National Focus：GER_remilitarize_the_rhineland | confirmed | GDI physical | left click / Start | 3782 / 0 | active 名称/cancel GUI + fresh v2 tracked progress；后续自然完成 | OFF |
| Production：首条 Kar98k 工厂 10→11，总分配 20/28→21/28 | confirmed | GDI physical | left click / add factory ×1 | 7391 / 11563 | 8 行身份/顺序、数字 AND 15 格 AND 全局总数；两次 SDK getter + 两次 GUI 双读 | OFF |
| Construction：state 64 新增 civilian_factory ×1 | confirmed | GDI physical | building icon 后 state click ×1 | 8594 / 1844 | GUI 队列精确 []→[(64,civilian_factory,1)]；两次 getter | OFF |
| Army：1. Panzer-Division → 第1集团军 | confirmed | GDI physical | right click army card ×1 | 14109 / 13140 | GUI 精确 Inf1+Panzer1 成员、无指挥官、Inf10 未分配；两次 getter | OFF |
| Frontline：GER_POL_mainland | confirmed | GDI physical | left click border ×1 | 17672 / 23109 | 三边界段、完整视口 mask、同一集团军/成员、白色方案、plan stopped；两次 getter | OFF |
| Offensive Line：GER_POL_mainland_Poznan_east | confirmed | GDI physical | right_drag ×1 / finally right-up | 17641 / 13469 | 同 Army/front，起点/尖端/目标线/集团军标签、方向及完整 mask 无额外订单；getter 内两次完整 signature 读回 | OFF |

Production 后续确认 11563 ms = SDK getters 3172+1672 ms + 原生 GUI 双读阶段 6719 ms。其他后续确认耗时来自对应 getter。各原结果与最终确认保持独立，未改写 uncertain 的历史。

## 持久化证据与单次提交

汇总：[gate-summary.json](artifacts/phase5/gate-20261006/gate-summary.json)。每次结果落盘后才进行下一项。七项各提交一次，重发次数为 0。

| Gate | 原始调用 | 最终确认 |
|---|---|---|
| Research / Focus | [research-focus-4.json](artifacts/phase5/gate-20261006/research-focus-4.json)，两项直接 confirmed | 同一文件内重复 GUI / telemetry 确认 |
| Production | [production-3.json](artifacts/phase5/gate-20261006/production-3.json)，uncertain | [production-readback-2.json](artifacts/phase5/gate-20261006/production-readback-2.json) |
| Construction | [construction-3.json](artifacts/phase5/gate-20261006/construction-3.json)，uncertain | [construction-readback-1.json](artifacts/phase5/gate-20261006/construction-readback-1.json) |
| Army | [army-assign-1.json](artifacts/phase5/gate-20261006/army-assign-1.json)，uncertain | [army-assign-readback-1.json](artifacts/phase5/gate-20261006/army-assign-readback-1.json) |
| Frontline | [frontline-4.json](artifacts/phase5/gate-20261006/frontline-4.json)，uncertain | [frontline-readback-2.json](artifacts/phase5/gate-20261006/frontline-readback-2.json) |
| Offensive | [offensive-2.json](artifacts/phase5/gate-20261006/offensive-2.json)，uncertain | [offensive-readback-1.json](artifacts/phase5/gate-20261006/offensive-readback-1.json) |

五项原 mutation 调用返回 uncertain 后均停止、重新观察，再修复有限 reader 校准并做只读确认；没有重发 setter/build/assignment/frontline/right_drag。最终确认以 original_action_id 关联原提交。七项之外，创建测试用第1集团军是必要准备，单独提交一次：[army-prepare-1.json](artifacts/phase5/gate-20261006/army-prepare-1.json)、[只读恢复确认](artifacts/phase5/gate-20261006/army-prepare-readback-1.json)。总计 7 个 gate 提交 + 1 个 Army 准备提交。

保留所有 rejected/uncertain/failed 文件：技术树默认 Infantry 页、生产数字/工厂格、地图标签 1px rounding、建筑计数、无将领人数的 serif 字形、边界动画及 World News 模态均经过重新观察。前线空状态曾在提交前被拒绝，审计 mutation_submitted=false；没有把这些尝试算成功。边界/工厂格只允许有限被动重读，不降低阈值或重复输入提交。

恢复导航曾误点“返回菜单”，只打开确认，随后正常点取消；没有确认退出/保存/读档。现已加入已知 native 菜单、World News、国策完成弹窗的提交前阻断，模态错误保持弹窗而不嵌套 Esc 菜单。

## 实现与验收边界

独立 GDI capture、SendInput、物理 CaptureProfile、F12/失焦/geometry/watchdog/deadline/ownership/finally release 保留。native 默认附加已有 GUI，旧 CU 路径仍需显式 backend 和 pump。没有自动启动游戏、自动 refocus 或 Agent 任意坐标接口。

新增限定 physical reader/calibration：实际生产数字及 AND 格读回；state 64 和 Amsterdam/Copenhagen/Warsaw 三锚点；已知三师、唯一第1集团军、1/2 人数、无指挥官；本土波兰前线和波兹南以东进攻线。底部 HUD 明确 +520px、中心弹窗 +260px，地图目标不按旧坐标任意缩放。完整订单 mask 允许 2px 边缘动画、最多 40 个额外/缺失像素；额外箭头、错误目标/标签、遮挡和错误 profile 测试拒绝。

校准可用 [build_phase5_templates.py](scripts/build_phase5_templates.py) 从保存的实机截图重建，来源/ROI/阈值见 [manifest.json](artifacts/phase5/templates/manifest.json)。语义目标和 GUI session 身份由已知 calibration 派生，非游戏内部稳定对象 ID；军事 telemetry 仍 UNKNOWN。视口外、遮挡/亚像素订单、其他 Army/general/camera/resolution、其他 native domain reader 保持 LIMITED / UNKNOWN / 未验收。不能将 seven-action 结果扩展成全部工具支持或“Computer Use 已完全可选”。

fresh telemetry 通过正常 GUI 有限推进产生；独立暂停监视先安装再解除暂停，最多 25 秒，通常 fresh 信号后立即暂停。没有放宽 30 秒 freshness guard。此前裸 space 请求被自动审批拒绝，未执行；改用限定暂停工作流后获准执行，没有尚待用户批准的七项 mutation。

## 回归与最终状态

完整 **389 passed / 10 subtests passed，32.55 s**；compileall、pip check、diff check 通过：[verification.json](artifacts/phase5/gate-20261006/verification.json)。首次完整回归为 388 passed + 1 个旧 loopback 测试 WinError 10053；该模块精准复测 2 passed，随后同一完整测试集全部通过，原日志保留。测试 Temp 使用仓库内独立目录，断言未放宽。没有项目外部 review 脚本，未新增 review 流程。

[最终截图](artifacts/phase5/gate-20261006/final/captures/native-0.png)：**GER / 1936-03-24 05:00 / paused**，保留测试前线与进攻线，plan stopped。原始起点为 1936-01-01 12:00，日期推进只用于测试准备/freshness，非自主战略 benchmark。Rhineland 已自然完成；basic_machine_tools 最后 fresh v2 frame 仍 researching。没有保存、加载或恢复测试前局面。

10 个原有存档（含 autosave）及 dlc_load.json 前后 SHA256 全部一致，无新增/删除：[baseline.json](artifacts/phase5/gate-20261006/baseline.json)、[final/files.json](artifacts/phase5/gate-20261006/final/files.json)。最终文件复核仅 capture/hash、input_count=0；其 legacy 截图对照不用于证明 gate 的 physical reader。

本轮没有 commit/push。**seven-action gate 完成后停止，等待下一步；不继续 AgentRuntime、其他 AI 接入或 autonomous benchmark。**
