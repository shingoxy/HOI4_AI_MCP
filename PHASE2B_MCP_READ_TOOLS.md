# Phase 2B — MCP Read Tools

日期：2026-09-30。用户已明确授权进入下一阶段。Phase 2A 的 Germany 1936、每日更新和读档回退满足只读 MCP 接入前置条件；未测的速度 1–5 精确性能不阻塞此接口。

当前交付：**COMPLETE / LIVE STREAM VERIFIED / EXTENSION LIVE VERIFIED / CODEX CHAT VERIFIED**。2026-10-01 宿主重启后，原有五个聊天工具实际调用成功；科研/国策 v2 扩展、33 项测试及 Computer Use 实机验收证据见 [PHASE2B_EXTENDED_TELEMETRY.md](PHASE2B_EXTENDED_TELEMETRY.md)。完整科研槽映射、当前国策 ID 和逐线生产仍为 UNKNOWN。

## Completed

- 官方 MCP Python SDK 2.2.0，stdio 本地服务，核心 5 个只读工具（v0.3.0 扩展至 7 个）、2 个 JSON 资源；无游戏执行工具。
- 后台 0.25 秒增量轮询，完整帧更新缓存；每次 poll 中接受的各帧均保留变化，不遗漏批量追加中的中间日期。
- 工业汇总只使用 Phase 2A 已实机证实的工厂总数；科研/国策/生产线未知项显式返回 UNKNOWN。
- 最多 100 条进程内变化，非消耗式 revision 查询、session ID、丢失历史标志；读档回退记录 timeline reset，日志重建记录 log reset。
- MCP 2026 资源订阅通知：状态更新、fresh/stale/unavailable 转换、读错误或 parser 错误变化后提示客户端重读。旧版客户端通过工具轮询。
- 启动回放以日志 mtime 估计时效；旧帧不会因 MCP 启动而自动变 fresh。文件不可读时返回 unavailable 和读错误。
- `scripts/check_mcp.py` 用官方客户端建立真实 stdio 连接，查询全部工具并退出。项目级 Codex 接入配置和 README 已准备。
- `--watch SECONDS` 保持同一服务进程，输出基线、通知后重读的状态/变化及结束计数；步骤见 [LIVE_VERIFY_PHASE2B.md](LIVE_VERIFY_PHASE2B.md)。不会操作游戏。

## Verified

| 验证级别 | 结果 |
|---|---|
| Phase 2A 回归 | 原有 15 项测试通过；Mod 和帧协议未改。全部测试在 `.venv` 中 **27 passed**，Python 语法检查通过；此前 `pip check` 通过，依赖未改变。 |
| 变化/时效测试 | 新增 6 项：旧日志基线、批量帧、去重、rollback、日志重建/读失败、stale 转换、历史上限与非法游标。 |
| MCP 协议测试 | 新增 4 项：只读工具/缺失日志/非法输入，资源订阅及重读，无新帧的 stale 通知，2025-11-25 初始化及 UTF-8 stdio。 |
| 持续验收命令 | 另增 2 项：模拟读档回退后通知/重读及 stale 转换，无通知时限时退出且不声称更新通过。初次真实 stdio `--watch 0.5` 启停通过；本次实机持续通知证据见下一节。 |
| 现有真实日志查询 | 通过官方 MCP 客户端读 `D:\Documents\Paradox Interactive\Hearts of Iron IV\logs\game.log`；GER、seq 706652、`24:00, 13 1月, 1936`、工厂 36/28/10，空 parser 错误。日志 mtime 为 2026-09-30 20:51:36（北京时间），查询正确返回 stale。该项是现有日志回放，不等价于实时新增帧验收。 |

## 实机持续验收：2026-09-30 21:47–21:54

操作者手工启动、推进、读档；Codex 仅运行官方 SDK 的 stdio 客户端。监听 session ID 始终为 `8843d312-9187-445c-9202-97b3c839e530`。

- 收到 **14 次**资源更新通知；按游标重读保留 **9 次 state_updated、1 次 log_reset、1 次 timeline_reset**，最终 revision 11。通知包括 10 次 fresh、3 次 stale、启动日志重建时 1 次 unavailable。
- 游戏新帧从 GER 的 1 月 6 日/706645 连续到 13 日/706652；政治力从 7.944 到 17.212，变化记录给出 before/after。游戏画面数值未逐项对照，不据此声称所有显示精度一致。
- 暂停超过 30 秒后收到 stale 通知，revision 不因时效变化增加；不再把旧帧标为 fresh。
- 读回较早存档后，在无新开局帧的情况下接受第二个较小每日序号：1 月 7 日/706646，revision 10，kind=timeline_reset，fields 为空；随后接受 1 月 8 日/706647、政治力 10.592，revision 11。读档后再次暂停也收到 stale。
- 每次重读的 parser_errors 均为空，log_read_error 均为 null。启动日志重建清除了旧状态，未将旧 1 月 13 日的状态冒充本次游戏数据。
- 所需条件已观察到后主动中断监听；没有 watch_finished 自动统计行，计数由已保存的 JSON 行重算。确认客户端及 run_mcp 子进程退出；没有关闭游戏或修改 Mod。

证据：[原始 MCP 通知](phase2b-live-20260930-214738.log)、[重算统计](phase2b-live-20260930-214738-summary.json)、[只读复制的 game.log](phase2b-game-20260930-214738.log)。原始 MCP 记录 UTF-8 无替换字符；归档 game.log 复查有 11 对完整 BEGIN/END、空 parser_errors，最新 seq 706647，与 MCP 最终状态一致。

## 限制与下一步

### 继续验证：实时更新与 Codex app-server

- 操作者继续推进当前游戏，两分钟监听正常结束：4 次 state_updated、5 次通知（含 1 次 stale），最终 GER、1 月 12 日/seq 706651，parser/read 错误为空。证据见 [phase2b-followup-summary.json](phase2b-followup-summary.json)，其中记录原始日志路径。
- 用本机 Codex 0.151.0 的 stdio app-server 实测 `mcpServerStatus/list`：发现全部 5 个只读工具和 2 个资源；`mcpServer/resource/read` 实际读取 current/capabilities，状态与真实日志一致。此次仅以进程参数临时禁用其他 MCP 和 apps/plugins；没有 thread/start、thread/resume 或 turn/start，没有运行模型，本次检查前后全局 config.toml 字节一致。证据见 [phase2b-codex-host-check.json](phase2b-codex-host-check.json)。
- 重启前当前聊天的直接 resources/list 返回 unknown MCP server，工具目录中无 HOI4 工具。2026-10-01 重启后实际调用五个核心工具成功，原阻塞解除，证据见 [phase2b-codex-chat-v1-verified.json](phase2b-codex-chat-v1-verified.json)。新字段实机验收及重启后 v2 七个聊天工具调用均已完成，后者证据见 [phase2b-codex-chat-v2-verified.json](phase2b-codex-chat-v2-verified.json)。
- app-server 方法语义依据 [OpenAI 官方文档](https://learn.chatgpt.com/docs/app-server#api-overview)，参数另用本机 CLI 生成的 schema 核对。没有修改全局配置，早先注册时的一致性未确认项继续保留。

- codex mcp get 初次未加载项目文件，随后用官方 CLI 注册到全局 MCP 列表；重启后当前聊天实际调用已验证。新服务版本的接入要求见扩展报告。
- 全局注册前后的其他配置语义比较返回 false。检查前完整快照未持久保存，无法确定具体差异或准确回滚；不能声称其他全局字段完全未变。现有服务器列表仍包含 jlceda、matlab、node_repl、obsidian、openaiDeveloperDocs；没有诊断或运行这些服务。已停止进一步全局配置修改。
- 初次观察 35 秒未有新帧；持续验收已补齐真实新帧通知、stale 转换及读档回退证据；原有五个宿主工具的调用也已验证。新字段已通过实机验证，新增聊天工具接入也已通过。
- MCP 旧版资源 subscribe 推送未实现；旧版握手/工具查询已验证，可轮询工具。
- 不扩展未经证实的研究/国策/生产字段；后续先确定数据来源，再改 Mod 协议及增加对应实机验收。
- Phase 2A 未完成的逐档速度和精确画面到日志延迟仍保留为未测项。

## Sources

- [官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)：本机安装并检查 SDK 2.2.0 的实际接口。
- [SDK 资源订阅说明](https://py.sdk.modelcontextprotocol.io/handlers/subscriptions/)：2026 listen 通知与旧版订阅的区别。
- [OpenAI 官方 MCP 配置说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)：项目级 `[mcp_servers.<name>]` stdio command/args 配置。
