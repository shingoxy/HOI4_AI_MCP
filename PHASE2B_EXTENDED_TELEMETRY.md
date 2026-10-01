# Phase 2B：科研与国策只读扩展

日期：2026-10-01。

状态：**COMPLETE / OFFLINE TESTED / LIVE VERIFIED / CODEX CHAT VERIFIED**。

2026-10-01 用户打开游戏后，Codex 已通过 Computer Use 自行进行正常 UI 测试，之前的应用授权阻塞已解除。已完成新字段实机验收；再次重启后当前聊天七个工具全部实际调用成功，新增工具接入也已验收。

## 已实现范围

| 字段 | 读取来源 | 范围和精度 | 新字段实机验证 |
|---|---|---|---|
| 科研槽数 | amount_research_slots 动态变量 | 当前 GER 的整数槽数 | PASS（见下方实机记录） |
| 三项科技研究中 | is_researching_technology | basic_machine_tools、construction1、electronic_mechanical_engineering，布尔值 | PASS（见下方实机记录） |
| 三项科技已完成 | has_tech | 同一固定列表，布尔值 | PASS（见下方实机记录） |
| 莱茵兰国策完成 | has_completed_focus | GER_remilitarize_the_rhineland，布尔值 | PASS（见下方实机记录） |
| 莱茵兰国策进度 | focus_progress 比较谓词 | 10% 宽的闭区间；完成时 [1,1]，没有伪造精确百分比 | PASS（见下方实机记录） |
| 生产汇总 | 原有工厂数动态变量 | 民用/军用工厂、船坞总数 | 已有 v1 实机证据；v2 完整帧与 get_industry 回归通过，未逐项核对 v2 工厂 UI |

固定跟踪对象不是当前所有科研项目，也不是当前国策 ID。槽到科技的对应关系、科研剩余时间、当前国策 ID、逐线生产仍为 UNKNOWN。零进度区间不证明该国策正在进行。

本机来源：

- `D:\Software\Steam\steamapps\common\Hearts of Iron IV\documentation\dynamic_variables_documentation.md`，amount_research_slots 第 156 行。
- 同目录 triggers_documentation.md，focus_progress 第 2882 行、is_researching_technology 第 6191 行。
- common/national_focus/germany.txt 第 8126 行确认当前 1.19.3 国策 ID 为 GER_remilitarize_the_rhineland；未沿用旧版本 GER_rhineland。
- common/technologies/industry.txt 和 electronic_mechanical_engineering.txt 确认三个科技 ID。
- common/scripted_triggers/GER_scripted_triggers.txt 使用 focus_progress 的进度比较语法。

## 协议、模型与 MCP

- Mod 新输出 protocol v2，仍为 BEGIN / 单行字段 / END。只使用临时变量、读取谓词与 log，没有 gameplay 写效果。
- Parser 接受 v1 和 v2；v2 扩展字段全部必需，提交完整帧前检查槽数、布尔值、科技状态互斥、活动跟踪数量和进度区间。
- v1 的 research/focus 返回 null，不把缺失字段解释为零；独立查询给出 section_status=unavailable。
- 新增 ResearchState、TechnologyState、FocusState。v1/v2 切换的变化检测支持新增/移除字段，避免旧 key 不存在导致异常。
- MCP 新版本为 0.3.0，共七个只读工具，增加 get_research/get_focus。能力资源声明固定对象、支持协议版本；extended_fields_live_verified=true 表示下方限定条件的实机测试通过，不保证任意国家/Mod。
- 项目 .codex/config.toml 只增加两个工具到白名单，原文件已备份到系统临时目录；未修改全局配置。

## 已验证

- `.venv\Scripts\python.exe -m pytest -q`：**33 passed，10 subtests passed**。
- v1 回归、完整 v2 帧、坏值、缺字段、重复字段、半帧、未知版本、v1/v2 切换、新字段订阅重读和 UNKNOWN 边界通过。
- Mod 日志模板与 Python wire schema 一致；静态检查括号平衡且没有列出的游戏状态写效果。这不是引擎编译或实机验证。
- Python compileall、git diff --check 通过。
- 官方 MCP 客户端对模拟 v2 日志建立真实 stdio 连接，七个工具查询成功；证据 [phase2b-v2-offline-mcp.json](phase2b-v2-offline-mcp.json)，明确标注 SIMULATED。
- 当前聊天在宿主重启后实际调用原有五个工具成功，读取已有 v1 日志 GER、1 月 12 日、seq 706651、空 parser/read 错误。证据 [phase2b-codex-chat-v1-verified.json](phase2b-codex-chat-v1-verified.json)。这是原五个工具的宿主接入证明；新 v2 字段通过独立新服务实机验收，随后当前聊天新增工具也已调用成功。

## 实机记录：2026-10-01

条件：本机 HOI4 1.19.3、Germany 1936；保留原有 Telemetry 加两个汉化 Mod 的选择（人名和部队名称汉化补充、原版汉化补全），**不是 only Telemetry 测试**。descriptor 指向项目源目录，本次新启动加载 protocol v2。正常选择科技/国策、推进、暂停和存读档；没有使用控制台作弊、Mod 写游戏状态或产品动作 Executor。

| 实机核对 | 结果 |
|---|---|
| 科研槽数 | 画面 4 个槽，v2 / get_research 的 slot_count=4 |
| 三项科技研究中 | 正常选择后 researching=true、researched=false；读档后的科研画面再次核对三项进行中 |
| 电子机械工程完成 | 原始日帧首次 completed：4 月 19 日 / seq 706748；完成通知已观察 |
| 基础机床完成 | 原始日帧首次 completed：6 月 11 日 / seq 706801；完成通知已观察 |
| 建筑技术 I 完成 | 原始日帧首次 completed：8 月 3 日 / seq 706854；完成通知已观察 |
| 莱茵兰国策 | 正常开始后记录全部十个 10% 未完成区间；首次完成为 2 月 4 日 / seq 706674，完成通知已观察，之后 [1,1] |
| 完成后的七工具查询 | seq 706883：三项 researching=false / researched=true，国策 completed=true / [1,1] |
| 存读档恢复 | 同一回退监听进程从旧 seq 706883，在没有新开局帧时接受第二个较小且向前的每日帧 seq 706641（1 月 2 日），发出 timeline_reset；科研/国策恢复未完成，后续更新正常 |
| 最终暂停 | 游戏 1 月 22 日 11:00；最新日帧 seq 706660（1 月 21 日 24:00），科技仍研究中，国策 [0.6,0.7]；暂停后查询 stale |
| 错误与生产汇总回归 | 原始日志 266 个完整 v2 帧、parser 错误 0；新服务所有检查的 parser/read 错误为 0；Telemetry 相关 error.log 命中 0。get_industry 仍返回汇总；v2 工厂 UI 未逐项复核 |

区间来自谓词，不把区间或进度条当作精确百分比；上述首次完成日期是每日采样日期，不是完成的精确游戏时刻。国策画面验证了开始、进展、完成及读档后恢复，未做每个区间边界的 UI 精确时间测量。

两次持续监听分别进行：

- 推进监听（1200 秒）：204 次通知、202 次 state_updated，暂停 stale 后继续更新；0 次 timeline_reset。该监听在读档前已经自然结束。
- 回退监听（240 秒）：新进程先回放旧 seq 706883，随后读档产生的新日帧进入同一进程；10 次通知、1 次 timeline_reset、9 次 state_updated。期间仍在推进，没有 stale 通知；最终暂停后的独立查询证明 stale。不能合并声称全程一个 MCP 会话。

### 证据

- [统计和 SHA256](phase2b-v2-live-summary-20261001.json)、[原始 game.log 字节副本](phase2b-v2-game-20261001.log)、[error.log 副本](phase2b-v2-error-20261001.log)、[Mod 选择快照](phase2b-v2-mod-selection-20261001.json)。错误日志存在其他游戏错误；仅 Telemetry 相关命中为零。
- [推进通知](phase2b-v2-live-20261001.jsonl)、[回退通知](phase2b-v2-rollback-20261001.jsonl)。前一份由 PowerShell Tee 管道保存，中文日期含替换字符；只用其数字/布尔状态和事件统计，准确中文日期以原始 game.log 为准。后一份由 Python 直接 UTF-8 写入。
- [升级后两个资源与七工具清单](phase2b-v2-resource-check-20261001.json)：能力声明已更新，状态 seq 706660、parser 错误为空。
- 七工具实际 stdio 查询：[研究进行中](phase2b-v2-live-tools-20261001.json)、[三项及国策完成](phase2b-v2-completed-tools-20261001.json)、[读档后暂停](phase2b-v2-rollback-tools-20261001.json)。数据来自真实日志，不是模拟。

### 存档变化

本轮新建 GER_1936_01_01_12.hoi4 测试存档，原手动存档 GER_1936_01_06_23.hoi4 仍在。游戏正常推进期间自动存档替换了原 autosave（原加载列表为 1942 年 11 月 4 日，后来为本轮 1936 年 9 月 1 日）；没有预先备份，当前存档目录没有备份文件。Codex 没有手工覆盖原手动存档；Mod 选择没有改变。

## 最终接入验收：通过

2026-10-01 操作者重启 Codex 后，当前聊天已发现并实际调用全部七个工具；get_research / get_focus / get_diagnostics / get_summary 及另外三个核心工具全部成功。返回 protocol v2、GER、seq 706660、1 月 21 日 24:00；科研 4 槽、三项研究中且未完成；莱茵兰未完成、进度区间 [0.6,0.7]，与归档一致。parser_errors=[]、log_read_error=null。暂停日志 stale 正常；freshness_basis=log_mtime_upper_bound、revision=0 是新进程回放基线，本次没有重新运行游戏或重复实机测试。

实际当前聊天调用证据：[phase2b-codex-chat-v2-verified.json](phase2b-codex-chat-v2-verified.json)。之前旧进程拒绝 v2 的历史证据保留在 [旧宿主诊断](phase2b-v2-old-host-20261001.json)，阻塞已解除。

Phase 2B 本轮限定范围验收完成；没有剩余接入步骤。完整科研槽映射/剩余时间、当前国策 ID 和逐线生产继续 UNKNOWN。未进入产品 GUI Executor、军队或生产控制阶段。
