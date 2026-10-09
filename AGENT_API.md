# Agent API

## 2026-10-07 Native time / shutdown 审计合约

这是 Native host / Runtime 的时间审计输出，不新增 GUI 操作范围或 provider 可调用工具。真实模型仍只接收 semantic Observation、Action Catalog、Goals、History；截图、ROI、坐标、HWND/PID、backend 与原始 Operator proof 保留在执行层私有证据中。

时间结果附带 `ownership_state`、`owns_running`、`operator_intervention_required`、`failure_evidence_error`。ownership_state 为 UNKNOWN / PAUSED_CONFIRMED / RUNNING_OWNED / STOPPING / STOP_FAILED_OWNED；后三者仍承担停机责任。正常暂停失败不得用 owns_running=false 掩盖。

GUI `pause_source` 与 telemetry `end_date_source` 独立。日期使用 fresh_telemetry_frame_received_at；暂停使用 validated_GUI_clock_glyph_stability / known_game_menu_template。`gui_date_status=UNKNOWN` 不等于未暂停，也不能把 telemetry 当作 GUI 暂停读回。

NativeRuntimeHost.close 返回 `shutdown`、`game_pause`、`stop`、`time_metrics` 和 ownership 合约。若 owned 未释放，则必须 `shutdown=unsafe_stop_failed`、`game_pause=UNKNOWN`、`operator_intervention_required=true`；正常清理标记不替代这些字段。time_metrics 包含 time_ownership_acquired/released、pause_attempts/failures、safe_stop_attempts/successes、modal_block_count、unknown_modal_count、operator_safety_interventions。

Modal classifier 返回 `state`、`names`、`stop_route`、`scope`。状态为 NO_MODAL / KNOWN_SAFE_MODAL / KNOWN_BLOCKING_MODAL / UNKNOWN_MODAL / OVERLAY_STACK。仅已校准菜单或有实际证据的单层 stop-only route 可恢复；UNKNOWN / OVERLAY_STACK 拒绝输入。NO_MODAL 只是当前 calibrated templates / centered rectangular candidate 范围内未检出，不能宣称全覆盖。

失败证据私有 JSON 明确 exact_rgb_available、captured_at/recorded_at、`ownership`、`ownership_after_failure`、telemetry、foreground 和 guard reason。guard 捕获失败则 exact RGB 不可用，禁止用前一帧或恢复后截图替换。

验收证据见 [Time Safety gate](artifacts/phase5/time-safety-20261007/TIME_SAFETY_GATE.md)；国家自治规划见 [COUNTRY_AUTONOMY_PLAN.md](COUNTRY_AUTONOMY_PLAN.md)。

新Construction single confirmed；新30天World News stop_route=null，真实报告unsafe_stop_failed / STOP_FAILED_OWNED / pause UNKNOWN / operator required；真实Codex仍NOT RUN。详见 [Phase5结果](PHASE5_AGENT_RUNTIME.md)。

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

## 2026-10-07 当前验收边界

**Phase 5：IN PROGRESS / MAP AND CLOCK REPAIR OFFLINE TESTED / CONSTRUCTION REVALIDATION FAILED。** 尚未达到“能用”。原seven-action 7/7、新Scripted工厂单轮confirmed和7天有限稳定性保留；原30天第21日失败不改写。本轮新的Construction单轮在提交前返回rejected / requirements_not_met，mutation_submitted=false、retry0；按用户附件“若任一关键验收失败，停在当前安全checkpoint”停止。新30天、真实Codex及multi-cycle均NOT RUN。


Action Catalog entry新增readiness：semantic_implemented、backend_supported、profile_calibrated、map_state、target_identity_valid。build需当前MAP_READY且独立state64身份有效，失配temporarily_blocked、profile未校准unsupported。profile calibration和当前camera状态分别记录。get_action_catalog只做私有只读GDI检查，不向Adapter返回图像、坐标或backend对象。当前home camera不支持原military绘图，相关动作保持unavailable。

Catalog preflight不能替代Executor：在state64/GER身份、当前queue、工具/模式和map最终检查后才commit。新实机build单轮rejected / requirements_not_met /7968ms，0提交、retry0，mutation readback NOT_ENTERED；说明完整工具选择流程仍未通过，不能因catalog available宣称native action成功。

Clock的GUI日期为UNKNOWN，pause证据可独立confirmed；最新日期只来自fresh telemetry frame。真实Codex provider/action/multi-cycle未进入，不把fake callback或CLI安装当接入成绩。其他action接口和52-tool注册范围未扩大。

当前报告：[本轮验证](artifacts/phase5/stability-20261007/verification.json)、[Construction run](artifacts/phase5/stability-20261007/construction-single-1/summary.json)、[事件和Operator proof](artifacts/phase5/stability-20261007/construction-single-1/events.jsonl)、[只读收尾](artifacts/phase5/stability-20261007/final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。

最终完整复核 **531 passed /10 subtests，46.85s**：[pytest-final2.txt](artifacts/phase5/stability-20261007/pytest-final2.txt)。前一次收尾复核有1项summary.tmp替换WinError5（530 passed）；原日志保留，相同失败组4/4及随后全量均通过，暂时权限/占用错误的根因仍UNKNOWN，未修改Runtime策略。

## 前一轮checkpoint（保留历史）

更新日期：2026-10-07。Phase 5 **SCRIPTED SINGLE MUTATION CONFIRMED / 7-DAY LIMITED RUNTIME STABILITY CONFIRMED / 30-DAY STOPPED AT DAY21**。全量493 passed / 10 subtests passed；真实Codex未进入。原single uncertain/later readback历史不改写；本轮单独授权的操作者准备不计Agent成绩。

Agent 的三个主要接口位于 `src/hoi4_operator/operator.py`：

```python
observation = operator.get_game_state("strategic")
catalog = operator.get_action_catalog()
result = operator.execute(action, arguments)
```

Agent 只接收 JSON-compatible semantic observation、catalog 和有限 history。窗口、进程、坐标、截图、模板和输入原语由私有 host 配置；Adapter 不接收 Operator、Executor 或 backend 对象。`execute` 仍支持历史语义接口，Phase 5 Runtime 另外执行七类动作的策略限制。模型提出的 action 必须先经过 schema、catalog 和 Runtime policy 校验。

## Observation

`summary` 只轮询 telemetry 和读取 GUI cache；`strategic` 按需串行刷新 research、focus、production、construction；`detailed` 额外按需读取已校准 military/front/order。不会扫描所有 GUI domain。GUI cache 使用 120 秒 TTL，telemetry 日期变化或 timeline reset 后失效。

每个 domain 返回 `status / data / source / freshness / complete / navigation_required / observed_at`。状态区分 `known / known_empty / known_zero / unknown / unsupported / partial / stale`。`complete` 只指明确 scope 中的字段或枚举；政治、工厂总数、三项科技和 Rhineland predicates 都有 scope，不代表完整政治、工业、科研或国策树。未枚举 Navy/Air/Trade 使用 unknown 和 `data=null`。

`navigation` 记录本次 GUI 页面读取结果及 safe-page restoration。GUI 读取并非完全 side-effect-free。读取失败会停止该次刷新，Runtime 在不稳定 observation 后停止计划。Research/Focus/Production/Construction 正常路径关闭面板；detailed Military 保留校准选中状态，并明确 `restored_safe_page=false`，不宣称完成通用军事页面恢复。

`alerts` 由确定性代码生成；仅对可靠 fresh 数据判断槽空闲、国策缺失、建筑队列为空、闲置军工、政治点数、空顾问槽、资源短缺、已知 Army 缺将领/前线、闲置 Air wing 和 telemetry stale。缺少证据时不产生告警。当前 native strategic 默认不会读取顾问、贸易、Air 或 Navy，因此这些相关告警通常不可判断。

## Action Catalog

每项返回 `status / reason / options / priority`；生产另有 `recommended`。状态为 `available / already_satisfied / temporarily_blocked / unsupported / unknown`。`options` 是本次允许的完整参数对象；Runtime 对 canonical JSON 严格比较，拒绝额外参数及 bool 冒充 int。

| Runtime action | 当前限定目标 |
|---|---|
| select_research | 已可靠读到的空槽；basic_machine_tools；已研究/研究中则 satisfied |
| select_focus | 已可靠读到 idle；GER_remilitarize_the_rhineland；已完成/已 active 则 satisfied |
| build | 已完整读到空队列；state 64 / civilian_factory / count 1 |
| set_production_factory_count | 首条 infantry_equipment_1；10、11、12 中与当前计数相差 1 的目标；仅向上调整作为 Scripted 推荐 |
| assign_divisions | 唯一已知 Army 只有 1 个成员时，分配已知且未分配的 1. Panzer-Division；不把 2 人 Army 扩到 reader 未支持的 3 人 |
| create_frontline | 已知 2 人 Army；已确认空订单视口；GER_POL_mainland |
| create_offensive_line | 同 Army 和唯一已知 mainland front；已确认无 offensive order；GER_POL_mainland_Poznan_east |

Catalog综合语义实现、native primitives、精确physical profile、校准manifest、fresh telemetry、GUI snapshot和目标约束。既有front/offensive标为satisfied；未知军事状态不会推测为空。Province/Navy/general Air、其他profile/camera/language和历史未native验收动作保持unavailable。Production仍限定10/11/12且Scripted保持目标12；12时无上调推荐，输出valid no-op。用户单独授权的12→11操作者准备已独立confirmed，随后全新Agent session自主11→12一次并confirmed。7天只证明有限Runtime稳定性，30天第21日的合法build提案被native地图校验拒绝，未提交、未重发；catalog available不保证当前地图viewport可解析。

Native production getter对runtime的infantry_equipment_1目标增加重复numeric AND 15-cell grid AND complete-list/global assigned MIL验证；其他行numeric/global证据保持partial。字形/网格阈值不降低、无OCR/LLM reader、被动等待不重发mutation。single gate要求已提交且confirmed的mutation≥1、有效fresh post-action observation和native/pump OFF；zero actions、already_satisfied或uncertain+later readback不能过关。完整证据见 [Phase 5报告](PHASE5_AGENT_RUNTIME.md)。

MCP v0.9.0 注册 52 个工具：历史 50 个工具保留，新增 `get_game_state(detail)` 和 `get_action_catalog()`。前者带可能 GUI navigation 的非只读 annotation；后者只读取 telemetry/cache。注册数量不代表 52 个 native live 支持项。

## Decision and Result

`AgentAdapter.decide(observation, action_catalog, history) -> AgentDecision`：

```json
{
  "assessment": "Use the known empty queue for civilian development.",
  "goals": ["Develop industry"],
  "actions": [
    {
      "action": "build",
      "arguments": {"state_id": 64, "building_type": "civilian_factory", "count": 1},
      "rationale": "The calibrated queue is confirmed empty."
    }
  ]
}
```

该例必须匹配当前 catalog 才能执行。拒绝未知字段、未知动作、不支持目标、重复动作、超预算计划及过长文本。仅记录简短 assessment/goals/rationale/actions，不请求 hidden chain-of-thought。

ActionResult 保留 `confirmed / already_satisfied / rejected / uncertain / timed_out / failed`。提交后没有自动重发；Runtime 先落盘，再判断结果并决定下一步。provider history 仅使用语义结果摘要；详细 GUI proof 留在私有审计文件。更多运行限制见 [AGENT_RUNTIME.md](AGENT_RUNTIME.md)。
