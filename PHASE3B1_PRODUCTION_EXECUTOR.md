# Phase 3B-1 — Production GUI Executor PoC

更新：2026-10-01。状态：**CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED（限定 PoC）**。

官方 MCP SDK stdio 实机客户端完成三项 `confirmed`：步枪生产线 10→12、12→10，支援装备生产线 2→3；另一次正常 GUI 操作将支援装备恢复到 2。每一步均读取同一行装备身份、数字和工厂格，最后再次读回；不是按点击次数宣布成功。逐线 telemetry 仍 UNKNOWN，确认来源明确为 GUI。

本轮只实现 Production snapshot 和 factory-count action。Phase 1 / 2 / 3A 的既有实机验收作为前提，没有重做；没有进入生产线创建、更换装备、删除、重排、Construction、Laws / Advisors、Army / Front 或 AI Player。

## 能力与证据来源

| 字段/能力 | 状态 | 本轮证据及限制 |
|---|---|---|
| 军工总数 | SUPPORTED | 现有只读 protocol v2 industry telemetry；实机为 28，与生产页总数一致 |
| 稳定 game line ID | UNKNOWN | 现有协议没有逐线 ID；未声称取得游戏内部 identifier |
| 当前行临时身份 | GUI_ONLY | session、snapshot version、装备标题/类别模板、priority 和 position；逐次重新验证 |
| 装备类型 | GUI_ONLY | 中文 GUI 类别名称与模板；`equipment_game_id=null`，不是内部 equipment ID |
| 完整装备身份 | PARTIAL | 六条校准行；第 3/6 条标题有省略号，`identity_complete=false / action_supported=false`，拒绝调整 |
| 当前 assigned factories | GUI_ONLY | 数字读回 **AND** 默认未放大的 15 格工厂图一致；实机验证 10/12 和 2/3 |
| line order/index | GUI_ONLY | 顶部六条完整可见行、优先级数字模板与行间距；没有 scrolling / reorder |
| 最大可分配数 | PARTIAL | `min(普通军工行上限150, 当前行数量+GUI未分配MIL)`；另有本 PoC 0–15 范围限制；特殊行不支持 |
| production efficiency | UNKNOWN | 未可靠解析，不以进度条长度代替数值；返回 null |
| current output | UNKNOWN | 未解析日/周单位和数量；返回 null |
| 逐线生产 telemetry | UNKNOWN | 没有新增该字段；不能把 GUI 数字写成 telemetry 确认 |

本轮没有扩展 Telemetry Mod、协议或解析器。采用用户允许的 GUI snapshot 路径，复用现有 fresh GER telemetry 作时效、时间线及军工总数交叉检查。新 API 能力资源单独注明 GUI 来源。

安装目录 `interface/topbar.gui` 的 `button_production / shortcut="Y"` 及真实 tooltip 已核对。`countryproductionlineview.gui` 的单行 111 高度、加减按钮及默认工厂格用于固定布局；`common/defines/00_defines.lua` 的普通军工行上限为 150，铁路炮等特殊上限不在支持范围。本机 Computer Use 原子 Y tap 有未响应情况：先检查实际面板，再回退到集中管理的入口点击。

## Snapshot 身份与动作

```text
official SDK client → MCP semantic tool → ProductionExecutor
                    → shared ComputerUseWorker / safety guard
                    → @oai/sky pump → normal HOI4 Production GUI
                    → numeric + factory-grid repeated readback
                    + fresh GER telemetry / MIL-total cross-check
```

```python
snapshot = get_production_lines()
line_id = snapshot["lines"][0]["line_id"]
set_production_factory_count(line_id=line_id, factories=12)
```

`get_production_lines()` 正常打开生产页并返回结构化结果。示例身份格式 `prod-<session>-0001-0001`，来自随机 session、snapshot version 和枚举序号，包含 `identity_source="gui" / stable_game_identity=false`；不把坐标当 ID。新的 getter 会生成新 version，旧 ID 失效。snapshot TTL 为 120 秒，成功调整更新数量并保留当前 ID；提交后不确定或失败使 snapshot 失效。

每次 setter 先检查参数、会话 ID、TTL、fresh v2 GER telemetry，然后打开生产页。全部六行的装备名称/类别、position、数量和全局已分配/总数必须与 snapshot 一致。每个单工厂加减前再读取完整页面及 telemetry，检查实际按钮模板后提交一次；随后要求全部行身份和数量符合预期，目标计数精确 ±1、全局已分配数精确 ±1、军工总数不变。最终独立观察再次确认目标数量等于 requested。期间读档 seq 回退、失焦或不一致均停止。

未知/新装备标题返回 `gui_identity_mismatch`；旧版本、顺序或数量变化返回 `production_snapshot_stale`；不在支持的顶部 viewport 返回 `target_not_visible`。重复名称拒绝；截断标题返回 `ambiguous_production_identity`。这是针对已校准 GUI 标题的匹配，不保证识别同名但内部 variant 不同的装备；此类身份扩展留作 UNKNOWN。

请求必须是非负严格整数，bool 和字符串不接受。超过 GUI 可用 MIL 或普通行上限先拒绝，超过本 PoC 15 格范围返回 `unsupported_factory_count`。由游戏 UI clamp、漏掉输入或读回不一致返回 `uncertain`，不会报告成功或再次提交。没有直接改变工厂总数、生产效率、库存、产量或正常分配机制。

## 模块与 MCP

| 文件 | 改动 |
|---|---|
| `actions/production.py` | GUI session-local IDs、snapshot version/TTL、身份签名、MIL-total 对照 |
| `executor/production_ui.py` | 面板定位、标题/类别匹配、数字分割和模板比较、工厂格交叉读回、加减按钮 |
| `executor/production_service.py` | 串行动作、逐步单次提交、重复确认、失败状态及计时 |
| `executor/catalog.py` | 集中 Production ROI、行布局及工厂格；高层没有 Win32 input |
| `executor/worker.py`、`scripts/computer_use_pump.js` | 仅增加 Y 到既有按键 allowlist；输入仍通过 Computer Use |
| `mcp_server.py` | v0.5.0，增加两个 Production 工具和明确的 GUI 能力说明 |
| `scripts/build_production_templates.py` | 本机裁剪及小型数字 masks；记录来源的 manifest |
| `scripts/phase3b1_client.py` | 官方 SDK stdio A/B/C/恢复测试，逐次保存原始结果 |
| `tests/test_production*.py`、`tests/test_mcp.py` | Production 及协议回归；旧七项查询与 Phase 3A action 保留 |

复用 Phase 3A 的 `UIState`、`Templates`、`ComputerUseWorker`、`Guard`、recovery 和动作锁；HOI4-AI 的模板匹配改编与 guard/scripted-hand 分层沿用既有实现及 MIT 许可，见 [THIRD_PARTY.md](THIRD_PARTY.md)。没有直接导入其训练、PPO、BC、learned visual policy 或 self-play，没有重写原生 Windows worker。

模板清单见 [manifest](artifacts/phase3b1/templates/manifest.json)。数字为本机安装字体提取的小 masks，header 为真实 GUI 颜色及 JPEG 样本。header 比较允许 ±1 像素平移，使用前景 IoU，保持 0.84 最低分和 0.10 候选差距，不拉伸字符；工厂数字需形状一致。工厂格同时识别正常绿色和新分配工厂的另一种显示状态，空格内区域必须为已校准暗色。没有 OCR / 大模型视觉参与每次动作。

MCP 接口只有 `line_id` 和 `factories`，不接受坐标或任意按键。getter 因正常导航改变界面，标注非只读、非 destructive；setter 标注非只读。默认服务不附加 GUI，返回 `executor_not_connected`。11 个工具中原七个查询保持只读，两个 Phase 3A 动作保留。离线 Executor 测试通过后才增加工具。

现有 `.codex/config.toml` 七查询 allowlist 及全局注册未修改；**当前聊天新增 Production 工具注册未验证**。本轮闭环证据来自真实官方 SDK stdio，而不是当前聊天工具发现。

沿用 Phase 3A 报告的 Computer Use 初始化和窗口选择，再启动测试客户端（需要已有游戏、fresh telemetry 和正在服务的 pump）：

```powershell
.\.venv\Scripts\python.exe scripts\phase3b1_client.py --window <现有HOI4窗口ID> --output artifacts\phase3b1\new-session.json
```

客户端默认执行 A/B/C/恢复四次正常调整；只获取生产 snapshot 可附加 `--snapshot-only`。`scripts/computer_use_pump.js` 的 `runGuiPump(45000)` 在同一已初始化 Computer Use 会话服务输入；无 pump 会 timeout，不自行启动或拉前台。

## Safety 与失败状态

保持 only hoi4.exe、显式 HWND/PID/进程名、失焦立即锁存停止、F12 emergency latch、独立 20ms watchdog 检查、12 秒 watchdog、90 秒 action timeout、10 秒 bridge timeout、无自动 refocus/launch。复用原子 click/key tap，没有新增 held-input 接口；结束时沿用既有释放/清理。失败时只有在 guard 仍允许输入的情况下尝试 Esc；不能失焦后向其他窗口发送恢复输入。

Production 不自动重试提交，`retry_count=0`。Y 无效后的入口 fallback 属于有界导航，不重复工厂提交。状态区分 `rejected / failed / timed_out / uncertain / confirmed / already_satisfied`；相同目标数量先重新验证 GUI 和 telemetry，再返回 already_satisfied，不调整工厂。客户端必须读取 status，不能只看 accepted。

Phase 3A 的 F12、失焦和停滞 watchdog 实机证据保持有效，本轮没有重演这些既有 live 测试。Production 的故障接入路径由 fake worker/telemetry 与已有 guard/bridge 测试回归覆盖；本轮新增实机证据只证明正常生产动作。

## 离线与实机结果

最终离线 **124 passed / 10 subtests passed**。包括真实生产截图解析、session/version/TTL、旧 ID、非法参数、装备/类别/顺序/数量改变、截断身份拒绝、增减/已满足、隐藏目标、stale telemetry、timeout、失焦/F12/watchdog、共享锁、漏点/clamp、提交后不一致、无 double-submit、官方 SDK schema/default-unattached，以及 Phase 1/2/3A 既有测试。真实失败 JPEG 的数字和 alternate grid 已作为回归 fixture。

运行命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Windows sandbox 对 pytest 临时目录和 SDK 子进程有访问限制，完整离线测试在批准的本地环境运行；未因此降低 game guard。测试日志见 [offline-tests.log](artifacts/phase3b1/offline-tests.log)。

实机条件：HOI4 1.19.3 / Germany 1936 / 中文 / **2560×1080 / UI scale 1.0** / 原有 Mod 组合。已有游戏窗口通过操作者授权使用 Computer Use；没有启动游戏、修改设置或 Mod 选择。支持顶部六条完整军工行（不含部分露出的第七行），默认未放大的 15 格布局，已校准身份及计数 0–15；实际三项 action 是第一/第二条。第三/第六条只观察，第四/第五条 setter 未实机验证，0/15 等端点未实机验证。

| 测试 | 生产线 | before→after | 状态 | snapshot ms | navigation ms | adjustment ms | confirmation ms | total ms |
|---|---|---|---|---:|---:|---:|---:|---:|
| A | Kar 98k式步枪 | 10→12 | confirmed | 16 | 875 | 5531 | 1156 | 8500 |
| B | Kar 98k式步枪 | 12→10 | confirmed | 31 | 2547 | 5500 | 938 | 9875 |
| C | 支援装备 | 2→3 | confirmed | 16 | 2593 | 2562 | 969 | 7000 |
| 恢复 | 支援装备 | 3→2 | confirmed | 15 | 2610 | 2641 | 906 | 7063 |

三项验收平均：snapshot **21 ms**、navigation **2005 ms**、adjustment **4531 ms**、confirmation **1021 ms**、total **8458.33 ms**。含恢复的四次平均 total **8109.5 ms**。各阶段和不等于 total：total 还包括前置 telemetry、安全及关闭面板。初始 getter total 2797 ms（其中 navigation 2766、snapshot 31），结束 getter total 2406 ms。

每次重复读回同一装备/position；军工总数均为 28，GUI 已分配随正常输入变化，最终回到 20/28。A 的 before/after telemetry seq 均为 706663，B 706663→706664，C 706664→706665，恢复 706665→706665。相同 seq 仍在 fresh 窗口内，不冒称 action 导致新的逐线 telemetry 帧；数字和格子才是逐线确认依据。运行前后 telemetry parser/read 错误均为 0。

原始 SDK 结果：[live-session-3.json](artifacts/phase3b1/live-session-3.json)。实机动作平均及恢复汇总：[live-summary-20261001.json](artifacts/phase3b1/live-summary-20261001.json)。

实机结束后新增截断标题只观察的拒绝分支、明确的 `equipment_type`/身份完整性输出，并重跑完整离线回归；第一、第二条的输入及数字/格子读回路径未改变。原始 live JSON 保留实测时的字段，没有事后补造新字段。

### 失败和修复

1. Session 1：SDK 客户端在 sandbox 创建 Windows stdio pipe 时 WinError 5，未进入 GUI；在批准的本地环境启动后解除。保留 stderr，不算 action 失败/成功。
2. Session 2：10→12 请求只执行了第一个增配，GUI 实际为 11；header JPEG 边缘导致数字识别拒绝，返回 `uncertain / production_number_unreadable`，自动 retry 0、没有 double-submit。新增前景平移匹配及 alternate assigned-grid 模板并通过真实样本回归，之后正常读档回到基线再进行 Session 3。该次不计入 confirmed。原始失败结果保留在 [live-session-2.json](artifacts/phase3b1/live-session-2.json)。
3. 人工模板采集期间的增减只用于校准，未计入三项实机验收。没有根据这些点击伪造 SDK success。

## 恢复、UNKNOWN 与技术债

Session 3 的 B 和恢复动作先通过正常 Production GUI 将原可见配置恢复为 `[10,2,1,2,2,1]`；最终 getter 也确认此配置。随后通过正常游戏菜单读取已有 `GER_1936_01_22_11.hoi4`，恢复测试前日期与局面，并暂停在 **1936-01-22 11:00**。使用真实截图再经同一 deterministic reader 核对六行及 20/28；见 [restored-readback.json](artifacts/phase3b1/restored-readback.json) 和 [恢复画面](artifacts/phase3b1/captures/final-restored.jpg)。

测试和排查期间游戏自然推进过日期，正常 autosave 被游戏覆盖；没有直接写、修改或替换存档文件。原手动存档沿用，不新保存测试局面。读档后没有推进新日帧，较晚日志缓存不计作恢复后的实时 telemetry。Mod 选择文件 SHA256 前后相同：`5e8a8d6d07ed63f2f456eb421ca83e370d4c00343a01abc0a835d00390ea3ff6`。

剩余 UNKNOWN / 限制：

- 稳定内部 line/equipment/variant IDs、效率、实际产量和逐线 telemetry；全标题模板不能证明同名 variant 的内部身份。
- 任意国家/语言/分辨率/UI scale/Mod 布局、未知装备、滚动和动态行高度、放大的工厂格；输入前的布局/模板检查会拒绝不支持状态。
- 数值/工厂格颜色以本机样本为依据，没有宣称覆盖所有生产状态；读回有歧义即停止。
- 无通用 modal 自动恢复。弹窗遮挡、暂停导致 stale 或按钮未响应会失败/不确定；有界 Esc recovery 不替代可靠读回。
- Computer Use pump 仍依赖当前会话，是 PoC 技术债；未重构为独立 native worker，未新增自动拉前台或游戏启动。
- 当前聊天新增工具发现/注册 polish 未验证，现有只读注册保留；真实 SDK action 已验证。

本阶段已满足限定 PoC 的三次 live confirmed 和完整离线回归，**停止在 Phase 3B-1**。
