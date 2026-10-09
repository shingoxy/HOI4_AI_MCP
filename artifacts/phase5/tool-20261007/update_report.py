"""Write this checkpoint once. Never rewrite historic live summaries."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.observation import game_datetime
from hoi4_operator.executor.native_audit import map_metrics

OUT=Path(__file__).resolve().parent
run=json.loads((OUT/'construction-single-1/summary.json').read_text(encoding='utf-8'))
events=[json.loads(x) for x in (OUT/'construction-single-1/events.jsonl').read_text(encoding='utf-8').splitlines()]
bootstrap=next(e['data'] for e in events if e['event']=='fresh_bootstrap')
selector=json.loads((OUT/'selector-native-1/result.json').read_text(encoding='utf-8'))
final=json.loads((OUT/'final-readonly-2/final-state.json').read_text(encoding='utf-8'))
last_date=game_datetime(final['read_only_telemetry']['game_date']).date().isoformat()
proof=dict(checkpoint='IN_PROGRESS_CONSTRUCTION_ACCEPTANCE_BLOCKED_BY_BOOTSTRAP_MODAL_PAUSE_FAILURE',
    tool_navigation=selector,construction_run=run,fresh_bootstrap=bootstrap,
    construction_acceptance='NOT_REACHED; no AgentRuntime observation/decision/action',
    new30='NOT_RUN',real_codex_provider='NOT_RUN',real_codex_action='NOT_RUN',codex_multi_cycle='NOT_RUN',
    real_model_calls=0,pump='OFF',full_regression=dict(passed=554,subtests=10,seconds=60.96,original_531_preserved=True),
    safety_stop=json.loads((OUT/'safety-stop-1/result.json').read_text(encoding='utf-8')),
    last_known_telemetry_date=last_date,last_known_telemetry_freshness='stale; log_mtime_upper_bound',
    final_gui_date=None,final_gui_date_status='UNKNOWN',final_paused=final['paused'],
    final_pause_source=final['pause_evidence']['pause_source'],
    manual_saves_unchanged=final['manual_saves_unchanged'],manual_save_count=final['manual_save_count'],
    mod_selection_unchanged=final['mod_selection_unchanged'],changed_files=final['changed'],
    time_control_safety_failure=True,uncontrolled_time_counted_as_benchmark=False,
    semantic_mutations=0,operator_strategic_interventions=0,operator_safety_pause_interventions=1,
    original_failed_runs_preserved=True,commit=False,push=False)
proof['selector_map_metrics']=map_metrics(OUT/'selector-native-1/native-audit')
(OUT/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''**Phase 5：IN PROGRESS / CONSTRUCTION TOOL NAVIGATION CONFIRMED / CONSTRUCTION ACCEPTANCE BLOCKED BY BOOTSTRAP MODAL PAUSE FAILURE。** 尚未达到“能用”。新30天及真实Codex未运行，实际模型调用0。旧seven-action 7/7、Production reader、Scripted single、7天及原21/30失败历史均保留，未重做。

本轮完整回归 **554 passed /10 subtests，60.96s**（原531保留，新增23）；相关79 passed，22.23s。原0.9模板、90%几何一致率、一像素位移、局部>=10和Production阈值保持。未commit/push、接其他模型或使用Computer Use；pump全程OFF。

| 本轮验收 | 真实结果 |
|---|---|
| 工具只读诊断 | 两组civilian和一组military，各只选工具一次，未点击建设州，queue前后[]。保存full RGB、ROI、首帧/稳定帧、map/modal/mode和原始NCC；不能把旧失败瞬间RGB的缺口改写成已补回 |
| 工具根因 | 旧selected模板在未激活工具时也匹配0.9594；实际激活后随边框循环动画在0.8959～0.9689变化。安装游戏GUI定义的start_construction_overlay引用两帧1.5fps循环sprite，与实机采样相符。hover、pulse和selected不能只凭一次NCC区分；没有证据证明DPI/GDI缩放、cursor或sprite替换为根因 |
| Reader | TOOL_NOT_SELECTED / SELECTED / ANIMATING / OCCLUDED / UNKNOWN。civilian图标core NCC>=.9、四边选中轮廓及正向construction mode联合确认，两次独立正向观察。最多3秒/12帧被动采样，不重发工具click；错误MIL工具或未知/遮挡拒绝。GDI cursor证据仍UNKNOWN。所有阶段先存PNG/ROI/JSON，Operator私有proof保存详细证据，provider history不接收 |
| 几何采样覆盖 | 新帧在1500-feature预算下局部只有7～9匹配；3000预算下局部20、全图93.8%～94.2%。只增加特征提取覆盖，不改变原匹配/位移/count阈值、目标点/区域或camera范围；小/大pan及遮挡仍拒绝 |
| 实机工具导航 | **TOOL_NAVIGATION_CONFIRMED**；一次工具click、两次正向truth，最终MAP_READY：665/714、93.14%、state64局部21。state64/GER独立身份、queue前后[]、paused=true；GDI physical2560×1600/DPI120，SendInput，0 semantic commit。结果先落盘后才启动新Agent session |
| 新Construction session | run **{run['run_id']}**：**BLOCKED BEFORE AGENT**，wall{run['wall_time_seconds']}s；observations0 / decisions0 / actions0 / results0 / confirmed0 / rejected0 / uncertain0 / mutation0。build及queue mutation readback根本没有进入，不能算Construction confirmed或action rejected |
| 直接阻断 | fresh bootstrap **failed / modal_blocked / paused=false / {bootstrap['duration_ms']}ms**。fresh telemetry已到1936-05-01，但正常暂停因modal抛错。Native trace只有一次Space resume，没有成功pause输入。GameTimeController.pause_owned在finally无条件清空owns_running，即使pause失败；close不再拥有停止路径，这是实质时间安全缺陷。此次没有自动retry或再次提交build |
| 后续安全处理 | 游戏在bootstrap失败后继续走时。之后真实截图包含新闻及科研完成叠层；该later frame不是精确bootstrap失败帧。操作者仅做**一次Escape安全暂停**，已校准菜单NCC1.0；随后独立只读确认paused=true、resumable=false。没有人工战略动作，但有1次人工安全干预，不能宣称无人工运行 |
| 时间证据 | bootstrap结束日期1936-05-01来自run内fresh telemetry；收尾日志最后已到**{last_date}**，但状态stale/log_mtime_upper_bound，只作last-known。GUI日期解码UNKNOWN；额外推进的时间全部不计benchmark，game_days仍0，不把它伪装成30天成功 |
| 地图审计 | prepare/require/capability和recovery起止单独记入native trace。Find View→Go to Capital→bounded wheel的attempt/success/failure/duration独立汇总，不隐藏于action duration。新session未进入观察，map各计数0；导航诊断的计数另列verification。无自动clock recovery route，clock_recovery_count=0 |
| 新30天 / 真实Codex | **全部NOT RUN**；Construction mutation gate前的时间安全gate失败后停止。真实provider boundary实现/新测试与真实推理不能提前接入，历史fake测试仍仅offline。无截图/坐标/backend进入任何模型 |

收尾9个手动存档、autosave与Mod哈希均未改变，无新增/删除，0 console/effect/memory/save编辑。首次收尾helper因host.templates属性错误未完成pause字段；原日志和PNG保留，第二次只读检查改为实际clock模板路径，已确认菜单暂停。当前NativeMapState在later未知叠层弹窗帧仍可能返回MAP_READY，不能据此宣称通用modal覆盖。

**剩余blocker：**先修复模态下时间ownership与独立停止路径，并保存clock失败精确RGB；明确未知/叠层modal的fail-closed范围。需新的fresh baseline后重新进行一次Construction mutation验收，再按30天→真实Codex→3–5 cycles顺序。依本轮附件停止规则，此checkpoint不继续修复或重跑gate，等待下一步。不得用工具导航成功或554项离线测试代替完整Construction/长期/模型实机验收。

证据：[verification](artifacts/phase5/tool-20261007/verification.json)、[工具真实诊断](artifacts/phase5/tool-20261007/diagnostic-2/result.json)、[实机工具导航](artifacts/phase5/tool-20261007/selector-native-1/result.json)、[新session](artifacts/phase5/tool-20261007/construction-single-1/summary.json)、[bootstrap事件](artifacts/phase5/tool-20261007/construction-single-1/events.jsonl)、[安全暂停](artifacts/phase5/tool-20261007/safety-stop-1/result.json)、[最终只读](artifacts/phase5/tool-20261007/final-readonly-2/final-state.json)、[完整回归](artifacts/phase5/tool-20261007/pytest-full-1.txt)。
'''
(OUT/'REPORT.md').write_text('# Phase 5 — 工具修复与bootstrap停止记录\n\n'+text.replace('](artifacts/phase5/tool-20261007/',']('),encoding='utf-8')
for name in ['STATUS.md','PHASE5_AGENT_RUNTIME.md','AGENT_RUNTIME.md','AGENT_API.md','ARCHITECTURE.md']:
    path=ROOT/name
    old=path.read_text(encoding='utf-8')
    title,body=old.split('\n',1)
    path.write_text(title+'\n\n更新日期：2026-10-07。本轮checkpoint。\n\n'+text+
        '\n## 前一轮checkpoint（保留历史，工具修复之前）\n'+body,encoding='utf-8')
print(json.dumps(dict(checkpoint=proof['checkpoint'],last_known_date=last_date,tests=554,paused=final['paused'])))
