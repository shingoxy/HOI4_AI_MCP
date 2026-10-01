# HOI4 AI Operator

Phase 3B-1 Production GUI Executor PoC 已离线测试及实机验证：生产 snapshot 和正常增减工厂，三次 confirmed，范围见 [Phase 3B-1 报告](PHASE3B1_PRODUCTION_EXECUTOR.md)。Phase 3A 的 Research / Focus 各三次实机确认及 Phase 2A / 2B 只读 telemetry 验收保持有效；阶段边界见 [STATUS.md](STATUS.md)。

```text
Telemetry Mod → game.log → FrameParser / StateCache → MCP stdio
                                                → changes / resource notifications
```

## 安装与检查

在项目根目录的 PowerShell 中运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\check_mcp.py
```

本机 `.venv` 已安装依赖。只部署运行环境时使用 `requirements-mcp.txt`。原 Phase 2A 测试仍可用原 Python 执行；缺少 MCP SDK 时 7 项协议/监听测试会显示 skipped，要完整验收须使用上述虚拟环境。

`check_mcp.py` 启动短暂的 MCP 子进程，调用全部 7 个工具后退出。默认定位 Windows Documents 下的 HOI4 `logs/game.log`；可用 `--log '完整路径'` 指定其他日志。没有日志时返回 `unavailable`，游戏长时间暂停通常返回 `stale`。这些命令不会启动 HOI4 或修改 Mod 选择。

实机持续更新验收使用 `scripts\check_mcp.py --watch 600`，在同一 MCP 进程内订阅并重读状态、变化和诊断，十分钟后退出。最短操作步骤和通过条件见 [LIVE_VERIFY_PHASE2B.md](LIVE_VERIFY_PHASE2B.md)。

## MCP 接入

本项目已准备 [`.codex/config.toml`](.codex/config.toml)，服务器名为 `hoi4_telemetry`，直接使用本项目 `.venv` 和绝对脚本路径。本机也已通过官方 CLI 注册到全局 MCP 列表，可用 `codex mcp get hoi4_telemetry --json` 检查。宿主重新加载配置后才可确认工具接入，当前聊天的工具列表不保证立即刷新。Codex 配置规则见 [OpenAI 官方文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。配置中的路径是本机路径，移动仓库后须更新。注册时的全局配置一致性未确认项见 Phase 2B 报告。

其他支持 stdio 的客户端使用：

```text
command: D:\Projects\HOI4 AI Operator\.venv\Scripts\python.exe
args:    ["D:\Projects\HOI4 AI Operator\scripts\run_mcp.py"]
```

| 工具 | 内容 |
|---|---|
| `get_summary()` | 最新完整 GER 状态、日期、seq、时效、解析错误 |
| `get_politics()` | 政治力、稳定度、战争支持度，附状态时效 |
| `get_industry()` | 民用/军用工厂和船坞总数；逐线生产标为 UNKNOWN |
| `get_research()` | v2 科研槽数、三项指定科技研究中/完成；完整槽映射和剩余时间 UNKNOWN |
| `get_focus()` | v2 跟踪莱茵兰国策的完成和进度区间；当前国策 ID UNKNOWN |
| `get_changes(after_revision=0)` | 本次进程内最多 100 条变化；重复查询不消耗记录 |
| `get_diagnostics()` | 日志读错误、parser 错误、日志 generation、未知字段 |

资源 `hoi4://state/current` 返回 JSON 状态；`hoi4://telemetry/capabilities` 列出可读范围及 GUI action 连接状态。以上七个查询工具标注只读，返回 `structuredContent` 和兼容的文本内容。v0.5.0 另提供 `select_research(slot, tech_id)` / `select_focus(focus_id)`、`get_production_lines()` / `set_production_factory_count(line_id, factories)`；四个 GUI 工具都标注非只读，getter 只导航/观察。默认启动不连接 Executor，返回 `executor_not_connected`。显式连接既有游戏窗口及 Computer Use pump 的方式见 Phase 3A 报告；Production 使用 session-local GUI ID，完整范围见 Phase 3B-1 报告。现有 Codex 接入配置仍仅启用七个查询工具，新增 GUI 工具当前聊天接入未验证。

## 时效、读档与通知

- 启动时先回放现有日志作为基线，不生成历史变化通知。基线时间使用整个日志 mtime，`freshness_basis=log_mtime_upper_bound`；其他日志写入可能使它偏乐观。增量帧使用 `frame_received_at`。
- 变化游标 `revision` 与游戏 `seq` 独立。保存 `session_id` 和 `latest_revision`；服务器进程重启后，新的 session 必须从 revision 0 开始。`history_truncated=true` 表示超过 100 条的旧变化已丢失，应重读 summary。
- 读档导致 seq 回退时，缓存仍按 Phase 2A 规则等待第二个向前的较小每日帧。随后记录 `timeline_reset`，不把两条时间线之间的数值差当作正常资源变化。日志重建记录 `log_reset`。
- 支持 MCP 2026 `subscriptions/listen` 的客户端可以订阅 `hoi4://state/current`。接受新帧、时效变为 stale、日志不可读或 parser 错误变化时发资源更新通知；收到通知后重读资源。旧版客户端可使用 `get_changes` 和 summary 轮询。通知不保证离线期间重放，也不会自动发聊天消息。

protocol v2 增加科研槽数、三项跟踪科技谓词和莱茵兰国策的 10% 进度区间；仍接受 v1 日志，缺失扩展数据明确返回 unavailable。新字段已通过 Computer Use 实机验证（Germany 1936，Telemetry 加两个汉化 Mod）；重启后当前聊天全部七工具已实际调用通过。运行中的旧 MCP 进程须刷新才能读取 v2 和两个新工具；仓库源码编辑不会自动重载。完整槽映射/剩余时间、当前国策 ID、逐条生产线效率保持 UNKNOWN。扩展范围与状态见 [PHASE2B_EXTENDED_TELEMETRY.md](PHASE2B_EXTENDED_TELEMETRY.md)，既有实机通知证据见 [PHASE2B_MCP_READ_TOOLS.md](PHASE2B_MCP_READ_TOOLS.md)。
