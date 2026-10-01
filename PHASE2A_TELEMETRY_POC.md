# Phase 2A — Read-only Telemetry PoC

状态：**CODE COMPLETE / OFFLINE TESTED / LIVE VERIFIED (GERMANY 1936 + SAVE/LOAD)**（2026-09-30）。默认测试 15 项通过；仅启用 Telemetry Mod 的实机开局、每日更新和读档回退已通过。速度 1–5 的完整对照及游戏画面日期变化到日志写入的精确延迟仍未测量。

## Completed

- 只读 Mod `mod/codex_telemetry`：对固定 Germany 玩家，在 `on_startup` 和 `on_daily_GER` 读取脚本变量，输出 `CODEX_STATE_BEGIN`、`CODEX`、`CODEX_STATE_END` 三行。序号使用 `global.num_days`，开局帧带 `origin=1`，供缓存处理读档时间回退。
- 协议 v1：每帧包含版本、序号、来源、游戏日期、国家 tag、政治力、稳定度、战争支持度、`manpower_k` 和三类工厂总数。Mod 不发送脚本命令、不调用作弊效果，不创建持久游戏变量。
- Python `LogTailer` 从 `game.log` 读取完整新行，检测文件截断、替换和临时消失；`FrameParser` 只提交序号相符的完整帧，错误存入有界列表；`StateCache` 保存最新状态、序号、游戏日期和 UTC 接收时间。`TelemetryService.get_summary()` / `get_politics()` 与本地 JSON 命令提供查询。
- 如果读档后 `global.num_days` 回退而没有开局帧，缓存会等待两个向前的较小每日序号再接受新时间线，避免单个旧帧回放使缓存倒退。
- `pytest.ini` 限定默认测试收集范围；`scripts/check_telemetry.py` 可只读报告日志存在性、BEGIN/END 数量、最新 seq/日期/状态、时效和解析错误。
- 安装脚本只创建 launcher `.mod` 指向仓库内 Mod，避免复制或覆盖游戏文件；若目标描述文件内容不同会拒绝覆盖。实机启动脚本会临时只启用 Telemetry Mod，并在游戏读取配置后恢复原 Mod 选择。描述文件已安装在 `D:\Documents\Paradox Interactive\Hearts of Iron IV\mod\codex_telemetry.mod`。

## Verified

| 级别 | 结果 |
|---|---|
| Static inspection | 本机 1.19.3 生成文档列出 `global.num_days`、政治力、稳定度、战争支持度、`manpower_k` 和三类工厂变量；参考项目有 `on_daily_TAG` + `set_temp_variable` + `log` 的实机先例。`python -m compileall -q src tests scripts` 与 `git diff --check` 通过。 |
| Unit test | `python -m pytest -q`：**15 passed**；`--collect-only -q` 只列出本项目测试，没有参考项目测试。 |
| Integration test | 用临时模拟日志运行本地 JSON 查询及 `scripts/check_telemetry.py`，得到结构化 GER 状态、序号 706640 和空错误列表；这是离线 CLI 检查。 |
| Live HOI4 | **已验证核心链路**：2026-09-30 操作者手工仅启用 `mod/codex_telemetry.mod`，进入 Germany 1936。`game.log` 有 15 组 BEGIN/DATA/END 完整帧，`parser_errors=[]`，游戏错误日志无 Telemetry 相关项。开局 seq 706640，运行至 1936-01-11 为 706650；读回较早存档后出现 706645、706646，缓存在第二个较小且向前的每日帧恢复，随后更新到 706647。暂停时无新增帧，超过 30 秒显示 `stale`。此前同时启用两个原有 Mod 的一轮也有真实帧，但不作为单 Mod 验收依据。 |

## Telemetry Fields

| Field | Status | Source | Example | Live Verified |
|---|---|---|---|---|
| `game_date` | 已实现，文本格式依游戏语言 | `[GetDateText]` | `24:00, 8 1月, 1936`（UTF-8 日志） | 是 |
| `seq` | 已实现，游戏日编号 | `global.num_days` | `706640` → `706650` → `706645` | 是 |
| `country` | 已实现，固定德国玩家 | `[THIS.GetTag]` | `GER` | 是 |
| `politics.political_power` | 已实现 | `political_power` | `2.324` → `14.564` | 是 |
| `politics.stability` | 已实现 | `stability` | `0.81` | 是 |
| `politics.war_support` | 已实现 | `has_war_support` 动态变量 | `0.35` | 是 |
| `manpower.available` | 已实现，由千人单位换算成整数人数，精度受原变量限制 | `manpower_k × 1000` | `1332620` → `1294172` | 是 |
| `industry.civilian_factories` | 已实现 | `num_of_civilian_factories` | `35` → `36` | 是 |
| `industry.military_factories` | 已实现 | `num_of_military_factories` | `28` | 是 |
| `industry.dockyards` | 已实现 | `num_of_naval_factories` | `10` | 是 |
| 当前 focus ID / 是否有当前 focus | UNKNOWN | 未找到可通用读取当前选择的变量 | — | 否 |
| active research slot / tech ID | UNKNOWN | 现有脚本只证实指定科技谓词及槽数 | — | 否 |
| Production Lines 明细 | UNKNOWN，暂缓 | Phase 1 未确认逐线读数 | — | 否 |

## Performance

| 项目 | 本阶段结果 |
|---|---|
| 更新频率 | 实测开局一次、每游戏日一次；开局当天的 daily 帧与 startup 帧共用 seq，缓存去重。暂停后 97 秒无新增帧。 |
| Speed 1–5 wall-clock latency | 两段实测日间隔约 49 秒与约 5 秒，但操作者确认档位并非速度 1→5；完整档位对照未测。 |
| game.log 增长 | 15 帧共 45 行、5895 字节 Telemetry 内容，平均 393 字节/帧；该次整个 `game.log` 为 6644 字节。 |
| Parser CPU | 监听进程运行约 31 分钟累计 CPU 约 2.23 秒；暂停时 10 秒采样 CPU 增量为 0，工作集约 10.3 MB。仅是本机一次采样。 |
| 游戏日期变化 → log → parser 接收 | 日志行时间到监听接收的样本：20:26:59 → 20:26:59.168、20:39:25 → 20:39:26.093；日志时间仅精确到秒。游戏画面日期变化到日志写入未量化。 |

## Failed

- 修复前 `ParserTests.test_malformed_value_and_duplicate_field` 失败：重复字段被识别，但后续 END 的次生错误覆盖了最后一项；解析器现忽略坏帧余下内容，当前 15 项测试全部通过。
- 默认沙箱命令通道返回 `helper_unknown_error: setup refresh had errors`；授权命令通道可正常运行测试和部署。
- 前次误在操作者工作时启动 HOI4，已关闭并恢复当时 Mod 选择；该轮无 Telemetry 帧。2026-09-30 的实机验收由操作者手工启动并切换 Mod，Codex 只读观察。

## Unknown

- 读档保持暂停时没有立即出现新 startup 帧；本次读档后缓存通过两个较小的每日序号恢复。不同存档/启动方式是否触发 `on_startup` 尚未普查。
- `manpower_k` 在日志中为千人浮点数；换算整数人数的精度仍受游戏变量本身限制。
- 其他 Mod/DLC 兼容性与 Germany 以外的玩家国家。本 PoC 有意只覆盖 Vanilla Germany 1936。
- 速度 1–5 的逐档延迟、游戏画面日期变化到日志写入的精确时间、长时间运行性能。

## Relevant Files

- `mod/codex_telemetry/descriptor.mod`
- `mod/codex_telemetry/common/on_actions/codex_telemetry.txt`
- `mod/codex_telemetry/common/scripted_effects/codex_telemetry.txt`
- `src/hoi4_operator/telemetry/{models,parser,tailer,cache,service,__main__}.py` 及 package `__init__.py`
- `tests/test_telemetry.py`
- `scripts/install_telemetry.ps1`
- `scripts/run_telemetry_live.ps1`
- `scripts/check_telemetry.py`、`pytest.ini`、`LIVE_VERIFY.md`
- `.gitignore`、`STATUS.md`、本报告

## Test Commands

在仓库根目录的 PowerShell 中，离线检查可随时执行：

```powershell
python -m pytest -q
python -m pytest --collect-only -q
python -m compileall -q src tests scripts
python scripts/check_telemetry.py
git diff --check
git status --short
```

日后重复实机验收可按 `LIVE_VERIFY.md` 操作。Phase 2A 实机验收由操作者手工启动游戏并切换 Mod；Codex 未改游戏 Mod 选择。

## Next Step

Phase 2A 核心实机链路已通过。随后用户已授权进入 Phase 2B，只读 MCP 交付见 [PHASE2B_MCP_READ_TOOLS.md](PHASE2B_MCP_READ_TOOLS.md)。速度 1–5 的完整对照和精确端到端延迟仍保留为未测项。
