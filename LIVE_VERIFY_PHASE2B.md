# Phase 2B：接入验收记录与复测

2026-10-01：科研/国策实机验证和重启后七个聊天工具调用均已通过，无剩余接入步骤。实际聊天证据见 [phase2b-codex-chat-v2-verified.json](phase2b-codex-chat-v2-verified.json)，游戏记录见 [扩展报告](PHASE2B_EXTENDED_TELEMETRY.md)。游戏现已暂停，Mod 选择未变。

如未来需要重新确认接入：

1. 重启 Codex，让 MCP 服务加载 v0.3.0。无需重新启动游戏或重做存读档测试。
2. 在本项目聊天发送：**“实际调用 hoi4_telemetry 的 get_research、get_focus、get_diagnostics，完成 Phase 2B 接入验收。”**

通过条件：七个工具可见；GER、protocol v2；科研 4 槽和三项进行中，国策未完成、区间 [0.6,0.7]（游戏仍保持本轮暂停状态时）；parser_errors=[]、log_read_error=null。暂停后 stale 正常。若后来推进了游戏，以最新真实日帧为准。

可选只读查询（在项目根目录 PowerShell）：

```powershell
.\.venv\Scripts\python.exe scripts\check_mcp.py
```

该命令新开短暂 stdio 会话，不会启动游戏或修改 Mod。它不能替代当前聊天新增工具的实际调用。

未来需要重测持续通知时运行 `scripts\check_mcp.py --watch 600`，正常推进、暂停 35 秒、存读档后推进两个游戏日；应出现状态更新、stale 与 timeline_reset。请使用独立测试存档并先备份旧 autosave：游戏推进会自动保存。直接控制台显示输出；归档时应由 Python 明确以 UTF-8 写入，避免 PowerShell 管道解码造成中文替换字符。

本轮 STATUS.md 已更新为 COMPLETE / OFFLINE TESTED / LIVE VERIFIED / CODEX CHAT VERIFIED。当前国策 ID、完整科研槽映射/剩余时间、逐线生产仍为 UNKNOWN。
