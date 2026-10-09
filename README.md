# HOI4 AI Operator

当前为 **Phase 5：IN PROGRESS**。WindowsNativeBackend 的 seven-action gate 已 7/7 confirmed；AgentRuntime 已实现，ScriptedAgent 单轮 mutation、Construction 单轮和有限 7 天稳定性已实机验证。最新 30 天测试因 World News 弹窗下无法确认安全暂停而失败；新增 stop-only Matrix 目前仅通过离线验证，World News 路径尚未启用。真实 Codex、其他模型和德国 180 天自治验收仍未完成。Computer Use pump 保持 OFF。逐项证据与限制见 [Phase 5 报告](PHASE5_AGENT_RUNTIME.md)、[原生后端](NATIVE_BACKEND.md) 和 [STATUS.md](STATUS.md)。

最新已完成全项目回归 **604 passed / 10 subtests passed**，保留 Phase 4 的 295 项基线；[本次提交前完整日志](artifacts/phase5/commit-20261009/pytest-full-1.txt)。离线通过不替代未完成的实机 gate。Phase 3 非军事 Executor 已完成限定验收并提交为 `2b1e1f3`；Research / Focus 和 Phase 2 只读 telemetry 的历史证据保留。

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

资源 `hoi4://state/current` 返回 JSON 状态；`hoi4://telemetry/capabilities` 列出可读范围及 GUI action 连接状态，以及 native/optional CU 和输入能力。以上七个查询工具标注只读，返回 `structuredContent` 和兼容文本。MCP v0.8.0 共 50 个工具，包含历史 Research / Focus / Production、Phase 3 非军事动作及 25 个 Phase 4 工具。默认启动不连接 GUI Executor，GUI 调用返回未连接结果；现有 Codex 配置未启用 Executor，新增 GUI 工具当前聊天接入未验证。

显式连接已有窗口时默认使用独立 native，方式见 [NATIVE_BACKEND.md](NATIVE_BACKEND.md)。旧 Computer Use pump 方式见 [Phase 3A 报告](PHASE3A_GUI_EXECUTOR.md)，旧验证客户端已明确选择 `--backend computer-use`。私有启动参数 `--gui-window` 指定实际窗口，`--non-military` 启用 Phase 3、`--military` 启用 Phase 4；它们不允许 Agent 通过动作参数传坐标或 backend。GUI getter 会导航，因此均标注非只读。军事对象 ID 是 session-local，刷新后必须使用新 ID。原生截图能够捕获当前显示，不表示所有 reader 已完成该显示的校准。

| Phase 4 工具组 | 范围 |
|---|---|
| Army / Division / General | 观察及创建第1集团军，单师分配 / 移除，任命曼施坦因；只覆盖三个已知师 |
| Front / Plan / Supply | 两处德波边界前线，整体计划执行 / 停止，单师补给 tooltip |
| Offensive Line | 独立 2048×1280 profile；第1集团军 / 单个装甲师 / 无将领，波兹南以东和波兰东北两个本土方向，要求订单视口为空 |
| Air | 单个 80/100 战斗机联队，东德意志 region 8，制空 / 关闭 |
| Navy | 单支 12 艘舰船 task force 观察；海域分配 / 任务未校准，拒绝 |
| 尚未支持 | `move_divisions`、`assign_fleet_region`、`set_naval_mission` 明确拒绝；任意分辨率 / camera 拒绝 |

工具列表发现、离线测试、人工校准与实际动作确认是不同证据。军事字段标为 GUI / derived / unknown，未扩展军事 telemetry；不支持通用军队、任意地图或完整海空军控制。历史官方 SDK 47 次 confirmed 保留，本轮增加 get_fronts ×2 和 offensive line ×2，具体计数及失败见 Phase 4 报告。

## 时效、读档与通知

- 启动时先回放现有日志作为基线，不生成历史变化通知。基线时间使用整个日志 mtime，`freshness_basis=log_mtime_upper_bound`；其他日志写入可能使它偏乐观。增量帧使用 `frame_received_at`。
- 变化游标 `revision` 与游戏 `seq` 独立。保存 `session_id` 和 `latest_revision`；服务器进程重启后，新的 session 必须从 revision 0 开始。`history_truncated=true` 表示超过 100 条的旧变化已丢失，应重读 summary。
- 读档导致 seq 回退时，缓存仍按 Phase 2A 规则等待第二个向前的较小每日帧。随后记录 `timeline_reset`，不把两条时间线之间的数值差当作正常资源变化。日志重建记录 `log_reset`。
- 支持 MCP 2026 `subscriptions/listen` 的客户端可以订阅 `hoi4://state/current`。接受新帧、时效变为 stale、日志不可读或 parser 错误变化时发资源更新通知；收到通知后重读资源。旧版客户端可使用 `get_changes` 和 summary 轮询。通知不保证离线期间重放，也不会自动发聊天消息。

protocol v2 增加科研槽数、三项跟踪科技谓词和莱茵兰国策的 10% 进度区间；仍接受 v1 日志，缺失扩展数据明确返回 unavailable。新字段已通过 Computer Use 实机验证（Germany 1936，Telemetry 加两个汉化 Mod）；重启后当前聊天全部七工具已实际调用通过。运行中的旧 MCP 进程须刷新才能读取 v2 和两个新工具；仓库源码编辑不会自动重载。完整槽映射/剩余时间、当前国策 ID、逐条生产线效率保持 UNKNOWN。扩展范围与状态见 [PHASE2B_EXTENDED_TELEMETRY.md](PHASE2B_EXTENDED_TELEMETRY.md)，既有实机通知证据见 [PHASE2B_MCP_READ_TOOLS.md](PHASE2B_MCP_READ_TOOLS.md)。
