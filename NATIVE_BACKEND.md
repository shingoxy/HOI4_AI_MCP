# Windows Native Backend

更新日期：2026-10-06。Phase 5 seven-action native gate **7/7 confirmed**，验收限定当前 physical profile 和目标；已按用户要求停止，等待下一步。

## 运行边界

[WindowsNativeBackend](src/hoi4_operator/executor/windows_native.py) 直接使用公开 Win32 API，不创建 Computer Use bridge，不 import `@oai/sky`，不依赖 Codex 会话。[native_win32.py](src/hoi4_operator/executor/native_win32.py) 隔离 ctypes ABI、GDI 与 SendInput；domain service 仍只依赖既有 InputBackend。MCP 默认不附加 GUI；明确提供既有窗口后默认采用 native，`--backend computer-use` 保留可选旧路径。

```powershell
# 窗口 ID 必须来自当前已打开 HOI4，不自动启动或激活。
.\.venv\Scripts\python.exe scripts\run_mcp.py --gui-window $selectedWindowId --backend native --non-military --military
```

仍使用原来的 50 个语义工具，协议版本 v0.8.0。Agent 参数中没有窗口 ID、capture profile、像素坐标或输入按钮。启动参数由操作者配置。

## 截图与坐标

使用桌面 DC 的 [BitBlt](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-bitblt)，只截取已绑定、前台 HOI4 的物理客户区，输出 top-down BGRA 后明确转换 RGB。临时采用 [PMv2 thread DPI context](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext)，结束恢复原 context，不更改进程/OS/游戏显示配置。此方案需要可见前台窗口；不支持最小化/遮挡后的后台捕获，没有实现 WGC/DXGI fallback。

当前 profile：

| 物理客户区 / DPI | 输出 | 范围 |
|---|---|---|
| 2560×1080 / 96 | 2560×1080 | 原校准坐标；本轮该显示未实测 |
| 2048×1280 / 96 | 2048×1280 | 原进攻线坐标；本轮该显示未实测 |
| 2560×1600 / 120，默认 physical | 2560×1600 | 七类限定 Germany 1936 GUI mutation 和重复确定性读回通过；具体目标见 Phase 5 报告 |
| 同上，显式 legacy | 2048×1280 | 1.25 输入映射 / bilinear 截图对照；与 CU 存在差异，未通过进攻线实机模板验收 |

默认 physical 保留物理像素。UIState 只对明确的 native 2560×1600 profile 开放面板，中心弹窗移动 260 像素，底部已知 HUD 移动 520 像素。当前 camera 使用新实机截图校准 state 64、三个城市锚点、本土波兰前线和波兹南以东目标；不按旧地图坐标缩放，不降低匹配阈值。来源/ROI 可通过 [模板脚本](scripts/build_phase5_templates.py) 重建。

截图成功不能证明 reader 或动作成功。七项本轮均有独立 readback confirmed：[逐项报告](PHASE5_AGENT_RUNTIME.md)、[机器可读汇总](artifacts/phase5/gate-20261006/gate-summary.json)。原调用 uncertain 时停止并只读确认，没有重发。其他 native domain/camera/resolution 保持 LIMITED/UNKNOWN，不能据此宣称全部 Computer Use 已可选。

## 输入与安全

实现内部 capture / click / key / scroll / left_drag / right_drag / geometry。`key_tap` 是 `key` 的别名，有限白名单为 Escape、Return、w/q/y/t/r、space；space 用于有限 fresh telemetry GUI 时间推进和暂停。键盘用 [MapVirtualKeyW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mapvirtualkeyw) 和 [KEYEVENTF_SCANCODE](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-keybdinput)；初始 virtual-key 导航未成功，扫描码修正后完成实机导航。

[SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput) 返回值必须完整，INPUT union 保留鼠标/键盘/硬件成员保证 Windows ABI。鼠标按物理 client offset、虚拟桌面（可有负原点）映射 absolute 坐标；`scroll` 保留 CU 的向下正值约定。

每次输入检查原有 only-hoi4.exe、HWND/PID、foreground、F12、watchdog/deadline。额外拒绝改变后的 geometry、未观察的点、已持按的用户输入、修饰键和目标点上的其他窗口；拖动途中也检查遮挡。输入前最多一次 down，拥有明确 ownership；finally 和独立 20ms 监视线程尝试 release。释放不移动鼠标、不按新键、不自动拉前台。release 失败保留 ownership 并使下一次 begin 拒绝。软件轮询和 Windows 释放尝试不是硬实时或崩溃后的物理保证。

`capabilities` 报告 capture/click/key_tap/scroll/left_drag/right_drag，`held_input=false` 表示不提供外部任意持按 API。CU wrapper 单独报告 right_drag 能力。

## 验证和续接

- 原生连续截图：3 次，78–94 ms；[对照](artifacts/phase5/capture-check.json) 只证明捕获，legacy 像素 MAE 不代表模板验收。
- pump OFF：原生扫描码打开科研面板、四空槽读回、native click 关闭并确认，mutation_count=0：[导航证据](artifacts/phase5/native-research-navigation.json)。
- 官方 SDK 独立 native stdio：50 tools，三项 telemetry 查询如实 stale：[SDK 证据](artifacts/phase5/native-sdk-read.json)。
- 原生其他输入异常、释放、DPI/geometry、Win32 资源、MCP lifecycle 的 fake 测试不注入 Windows 输入。

2026-10-06 用户已明确授权七项具体 mutation，七项全部完成。最终完整回归 389 passed / 10 subtests passed；10 个已有存档和 Mod 选择 SHA256 全部一致，结束 GER / 1936-03-24 05:00 / paused，计划停止。证据见 [Phase 5 报告](PHASE5_AGENT_RUNTIME.md)。客户端逐项先落盘，任何不确定结果停止，不重复提交。AgentRuntime、其他 AI 和 autonomous benchmark 未开始；等待下一步。
