# Phase5 repair checkpoint

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

完整531 passed /10 subtests，46.82s，原493保持；最终两个小修正（recovery标志初始化、profile calibration与map临时状态分离）后的相关111 passed，8.63s。最终全量531/10，46.85s，见pytest-final2.txt；前一次权限失败日志和4/4重检保留。默认沙箱临时目录WinError5失败单独保留，本机回归通过，不将其混作游戏证明。AgentRuntime/Scripted策略未修改；Kar98k目标仍12，native getter观察仍12。原single uncertain、later readback、single confirmed、7天与21天原始结果均保留。

当前报告：[本轮验证](verification.json)、[Construction run](construction-single-1/summary.json)、[事件和Operator proof](construction-single-1/events.jsonl)、[只读收尾](final-state.json)。完整531 passed / 10 subtests（原493保留）；最终相关111 passed。pump OFF，GDI physical 2560×1600/DPI120、SendInput；未降低模板/production/grid阈值。只读收尾确认paused=true，9个原手动存档、autosave及Mod哈希均未变，无新增/删除、console/effect/save编辑、其他模型或commit/push。

