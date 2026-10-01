# 项目状态

更新日期：2026-10-01

## 当前阶段

**Phase 3B-1：CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 Production GUI Executor PoC）。** `get_production_lines()` 建立 GUI 来源的 session-local snapshot，`set_production_factory_count(line_id, factories)` 正常增减工厂并精确重复读回。官方 SDK stdio 实机 3 次 confirmed（10→12、12→10、另一条 2→3），另一次 3→2 正常恢复。报告：[PHASE3B1_PRODUCTION_EXECUTOR.md](PHASE3B1_PRODUCTION_EXECUTOR.md)。本轮在 Phase 3B-1 停止，不进入 Construction / Laws / Army。

Phase 3A 保持 **CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED**；Research 和 National Focus GUI action 各 3 次 confirmed，既有安全 guard 实机证据保留，本轮没有重演。报告：[PHASE3A_GUI_EXECUTOR.md](PHASE3A_GUI_EXECUTOR.md)。

Phase 2B 保持 **COMPLETE / OFFLINE TESTED / LIVE VERIFIED / CODEX CHAT VERIFIED**；范围和既有证据见 [PHASE2B_EXTENDED_TELEMETRY.md](PHASE2B_EXTENDED_TELEMETRY.md)。

Phase 2A 保持 **CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED (GERMANY 1936 + SAVE/LOAD)**；证据见 [PHASE2A_TELEMETRY_POC.md](PHASE2A_TELEMETRY_POC.md)。速度 1–5 完整对照及游戏画面日期到日志的精确延迟尚未测量。

## 已实现

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
