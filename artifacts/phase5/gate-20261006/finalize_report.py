import json
from collections import Counter
from pathlib import Path
ROOT=Path.cwd()
p=ROOT/'artifacts/phase5/gate-20261006'
def read(name):return json.loads((p/name).read_text(encoding='utf-8'))
items=[
 ('Research','research-focus-4.json',0,None,None,'left click: Start research','GUI exact slot/basic_machine_tools AND fresh v2 researching predicate'),
 ('National Focus','research-focus-4.json',1,None,None,'left click: Start focus','GUI active name/cancel AND fresh v2 tracked focus progress'),
 ('Production','production-3.json',-1,'production-readback-2.json','production_readback','left click: add one factory','GUI numeric 11 AND 15-cell grid 11 AND global 21/28; full eight-line identity/order; repeated'),
 ('Construction','construction-3.json',-1,'construction-readback-1.json','construction_readback','left click: build in state 64','GUI full queue exact [] -> [(64,civilian_factory,1)]; two SDK getters'),
 ('Army','army-assign-1.json',-1,'army-assign-readback-1.json','army_readback','right click: assign to first army','GUI unique army/no general AND exact Inf1+Panzer1 membership AND Inf10 unassigned; repeated'),
 ('Frontline','frontline-4.json',-1,'frontline-readback-2.json','frontline_readback','left click: GER_POL_mainland border','GUI three border segments AND complete viewport order mask AND same army/divisions/White operation/stopped plan; repeated'),
 ('Offensive Line','offensive-2.json',-1,'offensive-readback-1.json','offensive_readback','one right_drag, finally right-up','GUI same army/front AND origin/tip/target/army label AND complete viewport mask/no extra order; full signature repeated')]
counts=Counter()
for f in p.glob('*.json'):
 d=json.loads(f.read_text(encoding='utf-8'))
 if isinstance(d,dict):
  for a in d.get('actions',[]):
   if a['result'].get('mutation_submitted'):counts[a['action']]+=1
rows=[]
for name,source,index,follow,key,primitive,reader in items:
 doc=read(source);a=doc['actions'][index];r=a['result'];proof=r if follow is None else read(follow)[key]
 assert r['mutation_submitted'] and proof['status']=='confirmed'
 assert counts[a['action']]==1
 assert doc['computer_use_pump']=='OFF'
 if follow:
  assert proof['original_action_id']==r['action_id'] and proof['new_mutation_submissions']==0
 for t in a['native_audit']:
  assert t['pump']=='OFF' and not t['held_input_remaining']
  for e in t['events']:
   if e['op']=='capture':assert e['profile']['name']=='GER_2560x1600_DPI120_PHYSICAL'
 duration=0 if not follow else proof['duration_ms']
 if name=='Production':duration+=sum(s['result']['duration_ms'] for s in read(follow)['actions'])
 rows.append({'action':name,'semantic_action':a['action'],'status':'confirmed','original_status':r['status'],
  'action_id':r['action_id'],'source':source,'readback_evidence':follow or source,
  'native_capture':'GDI BitBlt -> RGB / 2560x1600 physical / DPI120',
  'native_input_primitive':'SendInput.MOUSEINPUT / '+primitive,'mutation_call_ms':r['duration_ms'],
  'follow_up_readback_ms':duration,'readback_source':reader,'computer_use_pump':'OFF','mutation_submissions':1})
assert counts['create_army']==1 and sum(counts.values())==8
before=read('baseline.json')['files'];after=read('final/files.json')['files']
assert before==after
clock=read('offensive-readback-1-clock.json');assert clock['final_paused'] and clock['pump']=='OFF'
summary={'status':'confirmed','gate':'Phase 5 Native Backend seven-action gate','confirmed':7,'failed':0,
 'actions':rows,'source':'LIVE HOI4 / official SDK stdio / WindowsNativeBackend','computer_use_pump':'OFF',
 'submission_counts':dict(counts),'preparation':'create_army x1; recovered by two read-only getters; separate from seven gates',
 'final_game_date':'1936-03-24 05:00','final_paused':True,'plan_executed':False,
 'files':{'unchanged':11,'save_files':10,'mod_selection_files':1,'added':0,'removed':0,'changed':0,
          'baseline':'baseline.json','final':'final/files.json'},
 'agent_runtime_implemented':False,'other_ai_connected':False,'autonomous_benchmark_started':False,
 'scope':'Only calibrated Germany 1936 targets, exact physical profile and fixed map camera; other domains/cameras UNKNOWN or unsupported',
 'git_commit_push':'NOT REQUESTED / NOT PERFORMED'}
(p/'gate-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
verification={'pytest':{'status':'passed','passed':389,'subtests_passed':10,'seconds':32.55,
 'source':'pytest-final-recheck.txt','first_run':'388 passed, 1 WinError 10053 loopback failure; retained in pytest-final.txt',
 'precision_recheck':'tests/test_executor_transport.py: 2 passed; pytest-transport.txt'},
 'compileall':'passed','pip_check':'No broken requirements found','git_diff_check':'passed',
 'template_manifest':'artifacts/phase5/templates/manifest.json','gate_summary':'gate-summary.json'}
(p/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
phase='''# Phase 5 — Independent Native Backend and Pluggable Agent Runtime

更新日期：2026-10-06。状态：**NATIVE SEVEN-ACTION GATE 7/7 CONFIRMED / WAITING FOR NEXT INSTRUCTION**。Phase 5 整体尚未完成。

## 本轮结论与授权范围

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
'''
(ROOT/'PHASE5_AGENT_RUNTIME.md').write_text(phase,encoding='utf-8')
status=(ROOT/'STATUS.md').read_text(encoding='utf-8')
marker='## Phase 4 验收历史'
assert marker in status
status_head='''# 项目状态

更新日期：2026-10-06

## 当前阶段

**Phase 5：NATIVE SEVEN-ACTION GATE 7/7 CONFIRMED / WAITING FOR NEXT INSTRUCTION。** 当前 Germany 1936 测试局面的 Research、National Focus、Production factory count、Construction、Army assignment、Frontline、Offensive Line 全部以正常 GUI 完成一次 mutation 和确定性重复读回。每项成功先落盘；Computer Use pump 全程 **OFF**。

七项均为 native GDI BitBlt / physical 2560×1600、DPI120；输入为 SendInput，Army 使用一次 right click、Offensive 使用一次 right_drag，其余 mutation 为 left click。五项原调用 uncertain 后重新观察并做只读确认，没有重发；另有一次必要 Army 创建准备。逐项 confirmed、native capture/input primitive、duration 和 readback source 见 [Phase 5 报告](PHASE5_AGENT_RUNTIME.md) 与 [gate-summary.json](artifacts/phase5/gate-20261006/gate-summary.json)。

| Action | Gate | 原 mutation 调用 ms / 后续只读确认 ms | Pump |
|---|---|---|---|
| Research | confirmed | 5531 / 0 | OFF |
| National Focus | confirmed | 3782 / 0 | OFF |
| Production | confirmed | 7391 / 11563 | OFF |
| Construction | confirmed | 8594 / 1844 | OFF |
| Army | confirmed | 14109 / 13140 | OFF |
| Frontline | confirmed | 17672 / 23109 | OFF |
| Offensive Line | confirmed | 17641 / 13469 | OFF |

最终完整回归 **389 passed / 10 subtests passed**；compileall、pip check、diff check 通过。首次旧 loopback WinError 10053 已精准复测及完整复测通过，原失败日志保留。[验证证据](artifacts/phase5/gate-20261006/verification.json)。

结束 **GER / 1936-03-24 05:00 / paused**，保留测试前线/进攻线，计划停止。没有 console/effect/memory write/save edit、Mod 选择变更、人工保存/覆盖或读档。10 个已有存档及 Mod 选择文件哈希全部一致：[最终文件复核](artifacts/phase5/gate-20261006/final/files.json)。本轮没有 commit/push。

验收限定当前 physical profile、固定 camera 和已校准目标。其他 native domain/camera/resolution 未验收，军事 telemetry 仍 UNKNOWN，不宣称 Computer Use 已完全可选。**AgentRuntime、其他 AI 和 autonomous benchmark 均未开始；按用户要求停止，等待下一步。**

'''
(ROOT/'STATUS.md').write_text(status_head+marker+status.split(marker,1)[1],encoding='utf-8')
architecture=ROOT/'ARCHITECTURE.md'
a=architecture.read_text(encoding='utf-8').replace('For an explicitly attached `--military` runtime,','For the optional Computer Use `--military` runtime,')
a=a[:a.index('Phase 5 is **IN PROGRESS**.')] + '''Phase 5 is **NATIVE SEVEN-ACTION GATE 7/7 CONFIRMED / WAITING FOR NEXT INSTRUCTION**. The exact 2560×1600 physical client at DPI120 uses GDI BitBlt and SendInput with the Computer Use pump OFF. Calibrated native readers cover the seven limited Germany 1936 targets, fixed top UI, explicit bottom HUD offsets, state 64, three map anchors, first army with two known divisions/no general, the mainland Polish front and Poznan-east offensive line. The offensive tool requires its icon and three drawing-region patches; its readback verifies the origin/tip/target/army label and the full order mask. Failed/uncertain calls stop without resubmission; separate read-only confirmations link to the original action ID. The explicit legacy conversion remains unvalidated for the seven readers. Other cameras/resolutions/domains remain LIMITED/UNKNOWN. Strategic observation/catalog, AgentRuntime, adapters and autonomous benchmark have not begun. See [Phase 5](PHASE5_AGENT_RUNTIME.md) and [native backend](NATIVE_BACKEND.md).
'''
architecture.write_text(a,encoding='utf-8')
print(json.dumps({'confirmed':7,'counts':dict(counts),'save_mod_hashes_unchanged':len(after),'docs_updated':True}))
