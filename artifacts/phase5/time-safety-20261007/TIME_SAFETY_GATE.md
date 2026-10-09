# Phase 5 Time Safety gate — 2026-10-07

## 已落盘结果

| Gate | 结果 | 实际证据 | Ownership / 停机 |
|---|---|---|---|
| A：正常恢复、fresh telemetry、正常暂停 | PASSED，实机 | `live-A-1/result.json`；run `6a53a661-2d13-4abc-b963-c3009f87bb44`；advance 7563 ms | acquired/released=1/1；正常暂停 confirmed；无 safe-stop fallback |
| B：已知菜单阻挡正常暂停 | PASSED，实机 | `live-B-1/result.json`；run `056ddff4-1d7c-4b12-b436-66c54379187a` | 正常暂停失败 1 次，保留 ownership；独立菜单 readback confirmed；safe-stop success=1；acquired/released=1/1 |
| C：失败不丢 ownership、禁止自动重发 | PASSED，仅离线 | `pytest-time-3.txt`（104 passed，含 31 项新增 time-safety tests）；`pytest-full-2.txt`（585 passed / 10 subtests） | 覆盖 pause/guard/input/evidence/cleanup/circuit 异常；未故意在实机制造失控 |
| 新 baseline | PASSED，实机测试准备 | `live-baseline-1/result.json`；run `08664687-1c60-40e2-9797-785247cb7dc8` | GUI 暂停 confirmed、NO_MODAL、fresh frame_received_at；acquired/released=2/2 |

全部实机 capture 为 GDI BitBlt physical RGB，输入为 SendInput，Computer Use pump OFF。语义 mutation、Agent 决策、模型调用均为 0。A 与 baseline 的时间推进只用于安全验收 / fresh 测试准备，不计自主游戏日或自主战略行为。

A 的 fresh telemetry 到 `24:00, 3 8月, 1936`；baseline 到 `24:00, 4 8月, 1936`。GUI 日期仍 UNKNOWN；暂停依据来自实际 GUI clock glyph stability / 已校准菜单，而非 telemetry。

B 在正常地图运行时，以一次正常 Escape 主动打开已校准菜单。菜单阻挡正常 pause；独立停机读取菜单，未再次发送 Escape 或 Space。它证明已知菜单分支，不代表所有新闻、未知弹窗或 overlay stack 均可恢复。后两者仍 fail-closed。

B 的精确失败帧与 clock/modal/menu ROI 在恢复前保存于 `live-B-1/native-audit/time-failure-a9b3310b-d499-4356-b594-b401b1956a86/`。`failure.json` 记录实际 HWND/PID、foreground、UTC、telemetry、exact_rgb_available=true；ownership 从 STOPPING/owned=true 到 STOP_FAILED_OWNED/owned=true，再经双次菜单读回释放。没有用恢复后的菜单截图替换失败帧。

三个 live run 均 `shutdown=clean_no_owned_time`、`game_pause=true`、`operator_intervention_required=false`。operator_safety_interventions=0。

## 后续已执行结果

Construction single 已通过，run `577347d0-3ff3-4f0f-b4c4-c7a5ab5eb198`，state64/civilian_factory/1自主单次提交confirmed、13094ms、retry0、fresh post observation通过；结果先落盘后启动新30天。

新30天 `c6d10d44-d4f7-4916-8475-e08f81041d35` 失败：7 confirmed游戏日，fresh日期差8日；奥林匹克World News为KNOWN_BLOCKING_MODAL而无已校准stop_route。STOP_FAILED_OWNED保留、shutdown=unsafe_stop_failed、pauseUNKNOWN，需要人工安全暂停。真实Codex/multi-cycle未运行。A/B的通过不能泛化为所有新闻或长周期停机可靠。

## 当时的进入下一项条件（保留顺序说明）

只允许在以上结果落盘后启动全新 ScriptedAgent / NativeRuntimeHost / Observation / Catalog 的 Construction single gate；当前此文件落盘时尚未启动该 Agent。若单轮失败，停止后续 30 天和真实 Codex gate。原有 21/30 天失败记录、tool-20261007 和 seven-action 历史保持不变。
