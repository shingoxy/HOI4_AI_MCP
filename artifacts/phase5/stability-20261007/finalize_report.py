"""Read existing evidence and publish the stopped checkpoint, never resume a run."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
run_dir=OUT/'construction-single-1'
events=[json.loads(line) for line in (run_dir/'events.jsonl').read_text(encoding='utf-8').splitlines()]
run=json.loads((run_dir/'summary.json').read_text(encoding='utf-8'))
proof=next(e['data'] for e in events if e['event']=='operator_proof' and e['data'].get('action')=='build')
bootstrap=next(e['data'] for e in events if e['event']=='fresh_bootstrap')
final=json.loads((OUT/'final-state.json').read_text(encoding='utf-8'))
traces=[]
for path in (run_dir/'native-audit').glob('*.json'):
    data=json.loads(path.read_text(encoding='utf-8'))
    if 'trace_id' in data:
        traces.append(data)
commits=sum(e.get('op')=='semantic_commit' for t in traces for e in t['events'])
verification=dict(checkpoint='CONSTRUCTION_GATE_FAILED_STOPPED',phase='5 IN PROGRESS',
    map_root_classification='camera drift; pre-existing before old continuation; initiator unknown',
    new_gate=run,operator_result=proof,bootstrap=bootstrap,computer_use_pump='OFF',
    native_traces=len(traces),semantic_commit_events=commits,
    capture_methods=sorted({t['capture_method'] for t in traces}),
    held_input_remaining=any(t.get('held_input_remaining') for t in traces),
    mutation_readback_source='NOT_ENTERED; readback and confirmation timings zero',
    failure_frame_saved=False,failure_frame_gap='requirements_not_met occurred before final map require; map-only rejection persistence was not reached',
    final_paused=final['paused'],gui_date_status=final.get('pause_evidence',{}).get('gui_date_status','UNKNOWN'),
    last_fresh_telemetry_date=final['last_fresh_telemetry_date'],
    manual_saves_unchanged=final['manual_saves_unchanged'],mod_selection_unchanged=final['mod_selection_unchanged'],
    protected_file_changes=final['changed'],protected_files_added=final['added'],protected_files_removed=final['removed'],
    new_days30='NOT_RUN',real_codex_provider='NOT_RUN',real_codex_action='NOT_RUN',multi_cycle='NOT_RUN',
    model_inference_attempts=0,commit=False,push=False,
    original_failed_days30_preserved=True,full_regression_log='pytest-full3.txt',full_regression='531 passed / 10 subtests',
    final_related_regression='111 passed')
(OUT/'verification.json').write_text(json.dumps(verification,indent=2,ensure_ascii=False),encoding='utf-8')

status='''**Phase 5：IN PROGRESS / MAP AND CLOCK REPAIR OFFLINE TESTED / CONSTRUCTION REVALIDATION FAILED。** 尚未达到“能用”。原seven-action 7/7、新Scripted工厂单轮confirmed和7天有限稳定性保留；原30天第21日失败不改写。本轮新的Construction单轮在提交前返回rejected / requirements_not_met，mutation_submitted=false、retry0；按用户附件“若任一关键验收失败，停在当前安全checkpoint”停止。新30天、真实Codex及multi-cycle均NOT RUN。\n\n'''
detail='''当前报告：[本轮验证](artifacts/phase5/stability-20261007/verification.json)、[Construction run](artifacts/phase5/stability-20261007/construction-single-1/summary.json)、[事件和Operator proof](artifacts/phase5/stability-20261007/construction-single-1/events.jsonl)、[只读收尾](artifacts/phase5/stability-20261007/final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。\n\n'''
phase='''## 2026-10-07 地图和Clock修复checkpoint\n\n'''+status+'''
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

完整531 passed /10 subtests，46.82s，原493保持；最终两个小修正（recovery标志初始化、profile calibration与map临时状态分离）后的相关111 passed，8.63s。全量最终复核见本目录pytest-final.txt。默认沙箱临时目录WinError5失败单独保留，本机回归通过，不将其混作游戏证明。AgentRuntime/Scripted策略未修改；Kar98k目标仍12，native getter观察仍12。原single uncertain、later readback、single confirmed、7天与21天原始结果均保留。

'''+detail
runtime='''## 2026-10-07 当前停止点\n\n'''+status+'''
Native host在empty construction queue后只读验证当前map和state64/GER身份；Catalog返回各项readiness。最终提交仍独立重做地图/身份/选中工具检查，mode切换用同位置场景特征验证，不计算目标坐标。MAP恢复一次且经guard；恢复失败不会被伪装为成功navigation继续跑benchmark。该机制只读校准及531项回归通过，但新真实Construction单轮在selected-tool确认返回requirements_not_met，0提交，当前仍非可用验收状态。

Runtime沿原policy失效snapshots、summary重观察、quarantine并PLAN_STOPPED，没有retry。readback/confirmation未进入；不会把空队列、later observation或只读drawing4当mutation confirmed。新30天/Codex/provider/multi-cycle全部NOT RUN；旧21天failed run不改。下一步仅是调查工具状态与精确失败帧，不自动重复当前proposal。Clock暂停证据和telemetry日期来源独立，GUI日期不解析则明确UNKNOWN。

'''+detail
api='''## 2026-10-07 当前验收边界\n\n'''+status+'''
Action Catalog entry新增readiness：semantic_implemented、backend_supported、profile_calibrated、map_state、target_identity_valid。build需当前MAP_READY且独立state64身份有效，失配temporarily_blocked、profile未校准unsupported。profile calibration和当前camera状态分别记录。get_action_catalog只做私有只读GDI检查，不向Adapter返回图像、坐标或backend对象。当前home camera不支持原military绘图，相关动作保持unavailable。

Catalog preflight不能替代Executor：在state64/GER身份、当前queue、工具/模式和map最终检查后才commit。新实机build单轮rejected / requirements_not_met /7968ms，0提交、retry0，mutation readback NOT_ENTERED；说明完整工具选择流程仍未通过，不能因catalog available宣称native action成功。

Clock的GUI日期为UNKNOWN，pause证据可独立confirmed；最新日期只来自fresh telemetry frame。真实Codex provider/action/multi-cycle未进入，不把fake callback或CLI安装当接入成绩。其他action接口和52-tool注册范围未扩大。

'''+detail
for filename,insert in [('STATUS.md',status+detail),('PHASE5_AGENT_RUNTIME.md',phase),('AGENT_RUNTIME.md',runtime),('AGENT_API.md',api)]:
    path=ROOT/filename
    text=path.read_text(encoding='utf-8')
    first,rest=text.split('\n',1)
    path.write_text(first+'\n\n更新日期：2026-10-07。\n\n'+insert+'## 前一轮checkpoint（保留历史）\n\n'+rest.lstrip(),encoding='utf-8')

p=ROOT/'ARCHITECTURE.md'
text=p.read_text(encoding='utf-8')
start=text.index('Phase 5 is **')
end=text.index('\n\n',start)
text=text[:start]+'''Phase 5 remains **IN PROGRESS / CONSTRUCTION REVALIDATION FAILED**. The historical native seven-action gate remains7/7, scripted factory mutation confirmed and seven-day limited stability results are preserved; the original thirty-day run stopped at day21. New native map readiness and clock corrections have531 passing regressions plus10 subtests, but the new full Construction flow returned rejected/requirements_not_met before commit. New thirty-day, real Codex provider/action and multi-cycle gates did not run. Native uses GDI physical2560x1600/DPI120 and SendInput with pump OFF; no general camera/province support or other AI was added. See [Phase5](PHASE5_AGENT_RUNTIME.md) for the exact stopped result and evidence limits.'''+text[end:]
text+='''

`executor/native_map_state.py` adds private MAP_READY/MAP_RECOVERABLE/MAP_UNRESOLVED checks for the original gate camera and an independently observed Germany capital camera range, with state64-only fixed points. A single guarded normal-GUI recovery requires fresh city-anchor validation. Construction mode hides labels; last-submit validation uses the known tool/mode and unchanged feature positions across that overlay, without transforming a target. Catalog separates implementation/backend/profile/map/identity readiness, while Executor repeats checks. The current remaining blocker is selected-tool confirmation in the actual full flow; its precise failure frame is missing because frame persistence currently covers map rejection only. Clock modal detection precedes the dimmed-header check, and pause evidence is separate from unparsed GUI dates and fresh telemetry dates.
'''
p.write_text(text,encoding='utf-8')
(OUT/'REPORT.md').write_text(('# Phase5 repair checkpoint\n\n'+phase).replace('](artifacts/phase5/stability-20261007/',']('),encoding='utf-8')
print(json.dumps(dict(checkpoint=verification['checkpoint'],native_traces=len(traces),semantic_commits=commits,docs_updated=5)))
