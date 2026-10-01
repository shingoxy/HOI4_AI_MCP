# Phase 3A — Research / National Focus GUI Executor PoC

更新：2026-10-01。状态：**CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 PoC）**。

两个语义动作各完成 3 次真实正常 GUI 选择，均有动作后的新 telemetry 帧和 GUI 身份确认。没有进入 Phase 3B、Production、Army / Front 或完整 AI Player。Phase 1 / 2 的既有验收作为前提，未重新调查或改写 Telemetry Mod。

## 实现范围与条件

```text
test client / Codex → MCP action → Local Executor
                  → Computer Use @oai/sky → 正常 HOI4 GUI
                  → 正常游戏机制 → game.log telemetry + GUI 再观察
```

本机实际窗口为 **2560×1080 / UI scale 1.0**，HOI4 1.19.3 / Germany 1936 / 中文界面 / Telemetry 加原有两个汉化 Mod。因此使用实测布局，未切换到建议的 1920×1080，也未更改游戏设置。其他窗口尺寸在输入前拒绝；语言、国策树缩放/位置及不同 Mod 布局不保证兼容。

只支持以下已验证 ID，不承诺任意科技或国策：

| 动作 | 支持范围 |
|---|---|
| `select_research(slot, tech_id)` | 槽编号 0–3；`basic_machine_tools`、`construction1`、`electronic_mechanical_engineering` |
| `select_focus(focus_id)` | `GER_remilitarize_the_rhineland` |

高层接口没有坐标、任意键盘输入、任意 click、console、effect 或文件改存档操作。无 `set_technology`、`research all`、`complete_national_focus`、`eval_effect` 等状态修改路径。

科研流程读取 fresh v2 GER telemetry、校验槽数与完成标志，打开科研面板、识别目标槽框、进入分类、匹配节点、核对详情标题和可用研发按钮，执行正常研发及必要的更换确认。之后检查指定槽的科技名称，等待新日帧，要求目标 `researching=true / researched=false`，再重新观察槽身份并关闭面板。已有目标在该槽时返回 `already_satisfied`；目标在别的槽时拒绝。

国策流程要求 telemetry 未完成且政治面板为空闲状态；打开国策树、匹配莱茵兰节点、核对详情标题和可用 Start 按钮后正常开始。新日帧与政治面板上的目标名称、取消控件共同确认进行中，完成标志必须仍为 false。当前活动国策 ID 的来源明确标注为 GUI，telemetry 字段继续 UNKNOWN。无法取得组合证据时返回 `uncertain` 或 `timed_out`，不会把一次点击当作成功。

## HOI4-AI 复用与分层

检查参考项目当前 HEAD `73595d3` 的 `desktop.py`、`hand.py`、`scripted.py` 及 Rust Windows worker。没有现成编译 worker，且其 Python/Rust 入口耦合启动、训练和其他操作，所以没有直接导入整套 worker。

| 参考模块 | 本轮复用方式 |
|---|---|
| `scripted.Planner.find` | 在 `executor/templates.py` 改编 TM_CCOEFF_NORMED 查找方式，增加 ROI、缺失/低方差模板和有限得分检查 |
| Rust `desktop-worker` | 在 `executor/guard.py` 重新实现前台 HWND/PID/进程名称保护、独立 watchdog、F12 锁存、timeout |
| `hand.py` | 复用语义动作与低层输入分离的结构，未导入其其他领域依赖 |
| capture、mouse / keyboard | 通过已安装 Computer Use 的公开 `@oai/sky` API；未复制原 worker 的原生输入和 helper 协议 |
| recovery / release | 失败后在安全条件下尝试 Esc；动作结束清理观察状态。只有原子 click / key tap，没有 held-input 接口 |

MIT 来源及完整许可见 [THIRD_PARTY.md](THIRD_PARTY.md) 和 [license](licenses/HOI4-AI-MIT.txt)。没有 PPO、BC、learned visual policy 或 self-play 依赖。

新增模块：

- `actions/research.py`、`actions/focus.py`：telemetry 条件与确认结构。
- `executor/service.py`：串行动作、状态结果、时效校验、有限重试与提交后确认。
- `executor/catalog.py`：集中管理固定布局、槽位、分类和目标。
- `executor/ui_state.py`、`templates.py`：逐状态观察、确定性定位与身份检查。
- `executor/worker.py`、`guard.py`、`recovery.py`：本地 bridge、只读 Windows 安全查询与恢复。
- `scripts/computer_use_pump.js`、`phase3a_client.py`：Computer Use pump 和官方 SDK stdio 实机客户端。
- `scripts/build_phase3a_templates.py`、`check_gui_guard.py`：本机模板重建、只读实机 guard 验证。
- `tests/test_executor*.py`：fake telemetry/worker、真实裁剪匹配、MCP 与 bridge 边界测试。
- `requirements-gui.txt`：独立 GUI 依赖；开发依赖包含该文件。原只读部署可继续用 `requirements-mcp.txt`。

快捷键优先：`W` 打开科研、`Q` 打开政治、`Enter` 研发、`Esc` 恢复。本机 tooltip 和安装目录 `interface/topbar.gui` 已核对 W/Q；研发 tooltip 已核对 Enter。按键后检查实际 UI 状态，未切换才回退到集中管理的入口。Computer Use 原子 tap 在本机游戏中有未响应情况；没有通过延长原生 held key 绕过插件。模板匹配是自动程序执行，动作不需要大模型逐张解释截图，也没有 OCR 或视觉策略模型。

## MCP API、结果和安全

MCP v0.4.0 保留原七个查询工具及两个资源，离线 Executor 测试通过后增加两个 action tools：

```python
select_research(slot=0, tech_id="basic_machine_tools")
select_focus(focus_id="GER_remilitarize_the_rhineland")
```

返回包含 `accepted`、`action_id`、`status`、`duration_ms`、`retry_count`、`telemetry_confirmation`、`ui_confirmation`；错误附 `reason` 和恢复结果。区分 `rejected`（ID/槽/时效/安全前置拒绝）、`failed`（尚未提交的执行失败）、`timed_out`、`confirmed`、`uncertain`（提交后不能确定结果）。`accepted=true` 也可能超时或不确定，客户端必须读取 status。提交之后不重新选择；只有提交前的目标/面板查找失败可重试，最多 1 次。

Action tools 标注非只读、可能替换既有研究；telemetry 仍只读。capabilities 分别报告 `read_only`、`telemetry_read_only` 和 `gui_executor_attached`。默认 stdio 不附加游戏，动作明确返回 `executor_not_connected`。现有 `.codex/config.toml` 和全局注册没有修改，当前聊天的原七个工具与本轮 SDK action 验收不能混为一谈。

只读 WindowsProbe 验证 `hoi4.exe`、PID、前台窗口、存活和挂起状态；独立线程在 armed 期间约每 20 ms 检查。失焦不自动重新激活游戏。F12 在 worker 内锁存，须重启该 worker 才可继续。默认动作 90 s、worker request 10 s、watchdog 12 s；bridge 请求使用 loopback、随机 token、命令 ID 和过期检查。每次输入前再许可，错误后丢弃旧观察，安全条件满足才尝试 Esc。

自动输入全部是 Computer Use 原子按下/释放；Executor 不拥有持按键/鼠标状态，结束清理缓存。因此这里没有原 Rust worker 的原生“释放所有键”实现，也没有对插件内部崩溃时的物理释放作额外保证。20 ms guard 是软件轮询，非硬实时保证。以上边界保留为 PoC 限制。

不自动启动 HOI4、不改 Mod 选择、不自动解暂停。要获得动作后的新日帧，操作者须通过正常时间控制让游戏运行；暂停过久会拒绝 stale，暂停在已提交动作之后可能产生确认超时。

## 运行与离线验证

此 PoC 需要 Codex Computer Use 会话中的 pump，**不是脱离该插件即可运行的原生桌面服务**。

1. 在 Computer Use `node_repl` 初始化 `@oai/sky`，从 `list_windows()` 返回值选出唯一已经运行的 HOI4，保存为 `targetWindow`。使用返回的 `Window.id` 显式附加，不能猜测窗口。
2. 将 `scripts/computer_use_pump.js` 的内容作为 node_repl 代码载入。不要用 `eval`，本环境禁止字符串动态执行。
3. 在隐藏后台启动下面的 SDK 客户端，立即在已初始化 node_repl 调用 `await runGuiPump(45000)`。pump 先等 endpoint 最多 5 秒，每轮最长 55 秒；动作尚未结束时继续下一轮。CLI 自身不做任何原生输入。

```powershell
# $selectedWindowId 来自 Computer Use 返回的 Window.id。
.\.venv\Scripts\python.exe scripts\phase3a_client.py research basic_machine_tools --slot 0 --window $selectedWindowId --output artifacts/phase3a/research-live.json
.\.venv\Scripts\python.exe scripts\phase3a_client.py focus GER_remilitarize_the_rhineland --window $selectedWindowId --output artifacts/phase3a/focus-live.json
```

上述客户端分别启动带 `--gui-window` 的本地 MCP stdio；只运行一个附加 worker / pump。结束自动关闭 bridge 并删除 runtime endpoint。endpoint token、测试临时目录和存档备份已加入 gitignore。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp artifacts/phase3a/test-temp-new-run
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe -m pip check
```

最终结果：**79 passed / 10 subtests passed**；compileall、pip check、git diff --check 通过。包含 target lookup、错误 tech/focus ID、槽位、timeout、telemetry 新帧与 GUI 联合确认、retry 上限、失焦、F12、独立 watchdog、stale、already_satisfied、读档回退、不重复提交、错误详情与缺失确认、JPEG/PNG 解码、尺寸拒绝、bridge 鉴权及命令过期。原 Phase 2 测试继续通过。原 sandbox 测试临时目录有权限错误，改用项目内新 basetemp 并经批准运行后通过，未清理用户目录。

## 实机结果

用户已明确授权直接使用 HOI4 / Computer Use。游戏本来已运行，本轮未启动游戏。下表六次都由官方 SDK 调用语义 MCP action，再由 Executor 自动控制 GUI；人工准备、更换/取消操作和 `already_satisfied` 不计入成功次数。

| 真实选择 | duration_ms | before → after seq | 自动重试 | 状态 |
|---|---:|---|---:|---|
| Research slot 0 / basic_machine_tools | 19532 | 706650 → 706652 | 0 | confirmed |
| Research slot 1 / construction1 | 13735 | 706657 → 706659 | 0 | confirmed |
| Research slot 2 / electronic_mechanical_engineering | 8672 | 706664 → 706665 | 0 | confirmed |
| Focus / Rhineland 第 1 次 | 8922 | 706670 → 706671 | 0 | confirmed |
| Focus / Rhineland 第 2 次 | 8594 | 706676 → 706677 | 0 | confirmed |
| Focus / Rhineland 第 3 次 | 7000 | 706686 → 706687 | 0 | confirmed |

Research 平均 **13979.67 ms**；Focus 平均 **8172 ms**；六次总体平均 **11075.83 ms**。耗时包括 UI、Computer Use 传输、等待日帧及关闭面板，并非鼠标点击延迟。成功动作 parser/read 错误均为 0。

重复准备：旧 Jan 1 存档已选择三项研究与莱茵兰，因此通过正常 GUI 暂时将对应槽切换到合法但超前的原子能研究，再让 action 切回三个目标。国策通过正常 Cancel/确认后重复 Start；取消保留/损失进度完全遵循游戏规则，三次新日帧进度区间均为 [0.2,0.3]，没有直接完成国策。准备中还遇到挖掘科技前置条件不满足，该选项未启动。

失败与恢复记录：

| 记录 | 结果 / 处理 |
|---|---|
| `stale-rejected.json` | 输入前拒绝 stale，duration 0 |
| `research-1.json` | pump 先于 endpoint，worker_timeout；增加启动等待后重发 |
| `research-1-retry.json` | 实际截图为 JPEG，旧 pump 只接收 PNG，选择前失败；支持两种格式后重发 |
| `loss-of-focus.json` | 切换 Chrome 的 Computer Use 应用授权等待超时，pump 未供给；动作 worker_timeout、安全停止。不能作为失焦成功证据 |
| `guard-f12.json` | 真实 WindowsProbe + 独立线程锁存 emergency_stop |
| `guard-focus-loss.json` | 游戏内正常桌面快捷键使窗口失焦，真实 guard 锁存 loss_of_focus |
| `guard-watchdog.json` | 真实前台游戏、无控制器 heartbeat，1 秒测试 watchdog 返回 watchdog_timeout |

自动导航 retry 总数 0；因 bridge 修复人工重新发起 Research 调用 **2 次**。guard 验证的 elapsed_ms 从 arm 起算，包括等待操作者触发，不能当作精确输入到检测延迟。F12、失焦和 watchdog 实测没有 Executor 输入；完整 MCP 故障/恢复路径另由离线测试覆盖。实机 retry、确认超时后 uncertain 和错误国策 ID 的全部组合未逐一人为触发。

测试开始前备份原 autosave 和两份手动存档，正常 GUI 新建 `GER_1936_01_22_11.hoi4` 保存原局面。运行中正常日帧推进和较长应用授权等待使游戏自然推进到 4 月，国策和电子机械工程自然完成，自动存档也正常覆盖；没有 completion cheat。之后已通过正常读档恢复新建的 Jan 22 存档，GUI 核对三项原研究及莱茵兰进行中，最终暂停在 **1936-01-22 11:00**。两份原手动存档 SHA256 不变；原 autosave 备份保留在被忽略的 `artifacts/phase3a/save-backup/`，没有用文件覆盖游戏存档。

Mod 选择前后 SHA256 相同：`5e8a8d6d07ed63f2f456eb421ca83e370d4c00343a01abc0a835d00390ea3ff6`。最终读档后没有为刷新 telemetry 再推进日期；当前日志缓存可能仍是较晚时间线，不能将其当作恢复局面的实时 telemetry。下一次动作必须等正常运行产生新的有效日帧。

汇总与原始证据：

- [live-summary-20261001.json](artifacts/phase3a/live-summary-20261001.json)：每次 action_id、结果、平均延迟、安全结果、存档哈希。
- [原始 game.log](artifacts/phase3a/live-game-20261001.log)、[离线测试输出](artifacts/phase3a/offline-tests-20261001.txt)。
- 单次 `research-*-confirm.json` / `focus-*-confirm.json` 保存 MCP before / action_result / after。
- [恢复后的科研](artifacts/phase3a/captures/final-restored-research.jpg)、[恢复后的国策](artifacts/phase3a/captures/final-restored-focus.jpg)。
- `captures/` 为实际 JPEG 观察证据，`templates/` 为 PNG 裁剪；[manifest](artifacts/phase3a/templates/manifest.json) 记录来源和条件。

## 剩余 UNKNOWN 与停止边界

telemetry 当前国策 ID、完整 research slot assignment、精确剩余时间仍 UNKNOWN；本轮 action 所用槽身份/活动国策身份来自限定 GUI 模板。其他科技、国策、国家、语言、缩放、任意分辨率、滑动后的国策树和未知弹窗未验证，不能宣称通用支持。完整日帧延迟分布、跨进程多 worker、插件崩溃物理释放及当前聊天 action 注册未验证。

八项 Phase 3A 成功条件在上述限定范围内满足：正常 Research UI、正常 Focus UI、无 cheat/effect、联合确认、明确失败状态、安全保护、离线通过、真实 GUI/MCP 选择验收。当前阶段停止，不进入 Phase 3B。
