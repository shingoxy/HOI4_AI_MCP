# Phase 5 最终执行计划 — 当前 checkpoint

2026-10-07。来源为用户附件 `f29e3350-0856-433f-9e33-744a371eed94/已粘贴的文本.txt`，已完整读取。此次授权替代此前“一个 gate 失败即停止”的执行方式：普通 reader/calibration/modal/runtime/adapter 失败保存原始证据后自行修复、回归、重测，仅真实外部阻塞或无法安全暂停时要求操作者。

不新增 Phase 编号；Computer Use pump OFF，正常 GUI / WindowsNativeBackend，禁止 console/effect/memory/save 编辑、Mod 修改、原手动存档覆盖与自动 commit/push。新非 Codex 模型只在真实 Codex 验证之后接入；最终 Germany 1936 180 天能力与测试均属于 Phase 5。

## 历史基线（不重跑）

- seven-action 7/7 confirmed；Production single、7-day 有限稳定性、Construction single confirmed。
- Time Safety A/B live confirmed，C offline；585 passed / 10 subtests。
- 原21/30和最新fresh日期差8天（7个confirmed推进日）的失败原始文件保持不变。

## 本次进展

- 初始只读 preflight：`../time-safety-20261007/final-plan-preflight-1/final-state.json`；0 input，loss_of_focus，pause UNKNOWN。9手动存档、autosave、Mod哈希无变更。
- 已请求操作者暂停并保持 HOI4 前台；不自动 refocus 或启动。
- 已实现六态 stop-only Matrix，legacy `state` 保留用于旧 reader；新 `stop_state` 是停止策略分类，不改变导航许可。
- 新路径须提供 WindowsNativeBackend / pump OFF 的不可变 live proof、PNG哈希、两次菜单确认及菜单退出后modal identity不变；当前没有 World News live proof，因此 stop_route 仍 none。
- 完整回归 **604 passed / 10 subtests passed，74.00s**：`pytest-full-3.txt`；前两次沙箱 WinError 5 的原始日志保留。候选实机实验尚未开始，不计 Agent 行为或 benchmark。

## 后续 gate 顺序

用户最终执行计划全文保存在 [EXECUTION_PLAN.md](EXECUTION_PLAN.md)，不依赖本机附件路径。

1. World News bounded stop-only 实机证据；确认未关闭/确认新闻、menu paused、ownership release，退出menu新闻仍存在。
2. 新 fresh / paused / NO_MODAL baseline，新Scripted 30天；Runtime稳定性和策略覆盖分别评价。
3. 真 Codex inference → semantic confirmed mutation → 5cycles（稳定时最多10）。
4. 一个当前可用的非Codex模型，经同一Adapter/Observation/Catalog/Runtime完成真实动作及3–5cycles。
5. 德国1936和平期关键能力有限扩充，daily alerts / weekly AI / immediate supported events，尝试180实际游戏日。
6. 完整回归、证据/manifest/link检查，按真实完成度报告；禁止把PARTIAL/UNKNOWN/未实机项写为COMPLETE。
