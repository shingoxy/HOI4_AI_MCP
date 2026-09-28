# Phase 1 — HOI4 能力调查（2026-09-28）

## 结论和证据等级

目标版本为本机 Steam `Operation Postern 1.19.3.0.c01a (5632)`。本阶段只克隆参考项目、阅读源码和本机游戏脚本/生成文档；没有启动 HOI4、加载 Mod、执行输入或作弊命令。因此「脚本面存在」不等于「本机运行已验证」，「文档中未找到」也不等于引擎绝对不支持。

下表的 **Read State**：`数值`＝发现可求值的动态变量或参考项目实机日志；`谓词`＝只证实指定对象的真/假检查；`部分`＝仅覆盖汇总/子集；`UNKNOWN`＝没有足够证据。**Normal Action API** 指可供外部调用、保留正常成本、时间、效率和校验的玩家等价接口；`未找到`只是本次所查脚本/命令中没有证明它存在。**Requires UI** 指按本项目 Play Mode 约束完成相应玩家决策时要走本地 GUI Executor。**Cheat Only** 列列出发现的直接改状态命令/效果，不表示这些效果在所有 Mod 用途中都是作弊；它们在本项目 Play Mode 禁用。

证据索引（路径和行号以当前本机文件/克隆提交为准）：

- `G0`：`D:\Software\Steam\steamapps\common\Hearts of Iron IV\launcher-settings.json:4-5`（版本）。
- `G1`：同目录 `documentation\dynamic_variables_documentation.md`；例如 `date:977`、`political_power:743`、`stability:785`、`fuel_k:385`、`manpower_k:469`、`num_equipment:557`、`researched_techs:767`、`army_leaders:174`、`num_battle_plans:1262`。
- `G2`：同目录 `documentation\triggers_documentation.md`；例如 `can_research:1944`、`controls_province:2320`、`controls_state:2329`、`has_completed_focus:3501`、`has_idea:4034`、`has_railway_level:4628`、`has_tech:4882`、`has_war_with:5051`、`is_in_faction:5686`、`is_researching_technology:6191`、`owns_state:7001`。
- `G3`：同目录 `documentation\effects_documentation.md`；`add_building_construction:839-845`、`add_equipment_production:1207-1228`、`complete_national_focus:2870-2876`、`create_unit:3278-3298`、`log:4802-4808`、`set_technology:7805-7817`、`set_variable:7888-7901`。本机 effects 目录中未找到「选择科研槽并开始正常科研」「选择国策并开始计时」「给部队绘制计划」的已证实玩家操作入口。
- `G4`：同目录 `documentation\console_commands_documentation.md`；`add_equipment:166-170`、`instantconstruction:1062-1065`、`moveunit:1211-1214`、`research:1455-1467`、`teleport:1721-1725`。
- `G5`：`common\on_actions\00_on_actions.txt:1,243,5076,5770,5783`；`common\scripted_triggers\USA_scripted_triggers.txt`、`common\scripted_effects\00_scripted_effects.txt`、`common\scripted_guis\RAJ_tax_fraud_scripted_gui.txt:1-28`。证实 on action、可复用 trigger/effect、Scripted GUI 的脚本结构；Scripted GUI 示例是决议窗显示条件，不是对原版科研、生产或军队 UI 的外部 API。
- `R0`：[HOI4-AI 固定提交](https://github.com/noahsabaj/HOI4-AI/tree/73595d38c132d1c2bb10269effe09beb187972a7)（2026-09-27）。源码按 MIT 或 Apache-2.0 双许可，复用时仍需检查第三方 NOTICE。
- `R1`：[Windows worker](https://github.com/noahsabaj/HOI4-AI/blob/73595d38c132d1c2bb10269effe09beb187972a7/crates/desktop-worker/src/main.rs)：输入白名单 `297-318`，前台窗口与 PID `797-824`，Desktop Duplication/GDI 退化 `1115-1294`，SendInput `1363`，arm/apply/release `1852-1917`，750 ms watchdog `2737-2749`。仓库 STATUS 记载菜单截图、输入和远端实机检查，**不是本阶段重测**。
- `R2`：[ScriptedHand](https://github.com/noahsabaj/HOI4-AI/blob/73595d38c132d1c2bb10269effe09beb187972a7/src/hoi4_arena/hand.py#L19) 和 [Planner](https://github.com/noahsabaj/HOI4-AI/blob/73595d38c132d1c2bb10269effe09beb187972a7/src/hoi4_arena/scripted.py#L404)：组军 `404-423`、选将 `489-501`、前线 `523`、进攻线 `705`、执行 `767`；`hand.py:29-33` 明确仅校准第一支集团军。
- `R3`：[state_channel.py](https://github.com/noahsabaj/HOI4-AI/blob/73595d38c132d1c2bb10269effe09beb187972a7/src/hoi4_arena/state_channel.py#L1)：说明 2026-09-26 arena 实机日志 `1-45`，日更变量、领土掩码、将领/计划摘要 `66-157`。这证明 **该 arena** 的 Mod→`game.log`→读取器链路；没有证明任意国家/全部字段可通用。
- `W0`：随游戏安装的旧 Wiki HTML：`wiki\Research.html:119`、`wiki\Production.html:137-142`、`wiki\Battle_plan.html:47-85`。这些是早期 `hoi4wiki.com` 快照，仅作 GUI 概念佐证，不用于判断 1.19.3 数值或界面坐标。在线 [HOI4 Wiki](https://hoi4.paradoxwikis.com/Hearts_of_Iron_4_Wiki) 页面在本次工具访问时返回 401；Chrome 自动化连接和 Playwright 启动均失败，故 Modding、Scopes、Triggers、Effects、Variables、Scripted triggers/effects、On actions、Scripted GUI、Console commands **未完成在线逐页复核**。相应结论优先以本机游戏生成文档和脚本为准。

## Capability Matrix

| Feature | Read State | Normal Action API | Requires UI | Cheat Only | Evidence |
|---|---|---|---|---|---|
| Date | 数值：游戏日期 | — | 否 | — | G1 `date`；R3 |
| Political Power | 数值：总量/每日变化 | 未找到消费玩家动作接口 | 是，消费 PP 的玩家选择 | `add/set_political_power` | G1 `political_power`；G3；R3 |
| Stability | 数值 | 未找到 | 是，相关决策 | `add/set_stability` | G1 `stability`；G3；R3 |
| War Support | 数值（arena 已记录） | 未找到 | 是，相关决策 | `add/set_war_support` | G2 `has_war_support`；G3；R3 |
| Manpower | 数值/千人单位 | 未找到征兵操作接口 | 是，征兵法等 | 直接增减人力效果 | G1 `manpower_k`；R3 |
| Fuel | 数值/比例 | 未找到 | 是，相关生产/贸易 | `add/set_fuel` | G1 `fuel_k`；G2 `fuel_ratio`；G3 |
| Factories | 数值：各类总量、可用量 | 未找到玩家分配接口 | 是 | 直接建厂效果 | G1 `num_of_*factories`；G3 |
| Construction | 部分：建筑级数/历史总量；**队列明细 UNKNOWN** | `add_building_construction` 是脚本效果，非已证实玩家 API | 是，排队/调整 | `instant_build`、`instantconstruction` | G1 `building_level@type`/`total_constructed_*`；G3；G4 |
| Equipment Stockpile | 数值：按装备类型 `num_equipment@type` | — | 否（查看），补给决策需 UI | `add_equipment` / `add_equipment_to_stockpile` | G1 `num_equipment`；G3；G4；R3 |
| Production Lines | **UNKNOWN**：逐线装备、工厂数、效率/进度 | `add_equipment_production` 可新建线并传工厂、进度、效率；正常等价性未证实，调整现有线接口未找到 | 是 | 该效果可直接指定进度/效率，Play 禁用 | G3 `1207-1228`；W0 Production |
| Research | 部分：槽数、已完成科技、某科技是否正在研究；槽→科技/剩余时间 UNKNOWN | 未找到「选槽→选科技→正常计时」接口 | 是 | `set_technology`、console `research`/`roic` | G1 `researched_techs`；G2 `can_research`/`is_researching_technology`；G3；G4 |
| National Focus | 谓词：指定国策已完成；当前国策/进度 UNKNOWN | 未找到「选择→开始计时」接口 | 是 | `complete_national_focus` | G2 `has_completed_focus`；G3；W0 |
| Laws | 谓词：逐一检查 `has_idea`；arena 枚举三类法 | 未找到玩家购买接口 | 是 | `add_ideas` 等直接效果 | G2 `has_idea`；G3；R3 `96-102` |
| Advisors | 部分：`political_advisor`、角色/人物存在性；可雇名单和价格 UNKNOWN | 未找到玩家雇用接口 | 是 | 人物/idea 直接效果 | G1 `political_advisor`；G2 `has_character`/`has_idea` |
| Army | 部分：将领列表、orders group 数 | 未找到玩家组军接口 | 是 | `create_unit` 不等于组军 | G1 `army_leaders`/`num_orders_groups`；G3；R2；R3 |
| Divisions | 部分：数量、州内分布、师 scope 可枚举；精确命令链 UNKNOWN | 未找到玩家编入集团军接口 | 是 | `create_unit`/`delete_unit` | G1 `num_divisions`；G3 `every_country_division`；R2/R3 |
| Generals | 部分：将领列表/所辖师数；详细任命状态可进一步验证 | 未找到玩家任命接口 | 是 | `create_corps_commander` 是直接创建 | G1 `army_leaders`/leader 数值；G3；R2/R3 |
| Frontline | 部分：计划数可读；线的几何和归属 UNKNOWN | 未找到绘线脚本接口 | 是 | `moveunit`/`teleport` 均不能替代 | G1 `num_battle_plans`；G4；R2 |
| Offensive Line | 部分：计划数；几何/目标/执行状态 UNKNOWN | 未找到绘线脚本接口 | 是 | 同上 | G1 `num_battle_plans`；G4；R2 |
| Battle Plan | 部分：计划数、平均 planning/ready；完整命令树 UNKNOWN | 未找到正常执行计划接口 | 是 | `boost_planning` 是直接效果 | G1 leader 数值；G3；R2/R3 |
| Supply | 部分：补给节点数、车辆需求/库存等；逐师补给状态 UNKNOWN | 未找到玩家操作接口 | 是，枢纽/车辆等设置 | `supply_units` 等直接效果 | G1 `num_of_supply_nodes`；G3 `get_supply_vehicles` |
| Railways | 谓词：指定铁路级别/连接 | `build_railway` 是效果，非玩家 UI API | 是，建造/升级 | 直接建铁路效果 | G2 `has_railway_level`/`has_railway_connection`；G3 `build_railway` |
| Air Force | 部分：经验、已部署人力等；逐联队任务/基地 UNKNOWN | 未找到玩家任务接口 | 是 | 直接生成/改状态效果需排除 | G1 `air_experience`/`deployed_airforce_manpower_k` |
| Navy | 部分：舰数、将领列表等；舰队任务明细 UNKNOWN | 未找到玩家任务接口 | 是 | 直接创建海军等效果需排除 | G1 `num_ships`/`navy_leaders`；G3 |
| Diplomacy | 谓词：指定关系/行动条件；完整关系表 UNKNOWN | 未找到玩家外交动作接口 | 是 | 强制宣战/吞并等效果不适用 | G2 外交/战争触发器；G3 |
| Wars | 谓词：指定国家间战争/战争目标；详细战况 UNKNOWN | 未找到玩家宣战接口 | 是 | 直接宣战效果需排除 | G2 `has_war_with`；R3 arena 事件 |
| Factions | 部分：成员/领袖动态变量、指定成员关系 | 未找到玩家加入/邀请接口 | 是 | 直接改阵营效果需排除 | G1 `faction_members`/`faction_leader`；G2 `is_in_faction` |
| State ownership | 谓词：对指定州 `owns_state`；可有限枚举 | — | 否（读取） | `transfer_state` 等直接效果 | G2 `owns_state`/`controls_state`；G3 `every_owned_state`；R3 |
| Province control | 谓词：对指定省份 `controls_province`；可有限枚举 | — | 否（读取） | `set_province_controller` | G2；G3；R3 arena 掩码 |
| Intelligence | 部分：对目标国各类 intel、机构存在、特工集合；任务/网络明细 UNKNOWN | 未找到玩家操作接口 | 是 | `add_intel`、直接创建机构效果 | G1 `*_intel`/`operatives`；G2 `has_intelligence_agency`；G3 |

### 四个重点系统的判定

1. **Research**：已证实可读槽数、已完成科技、某项正在研究的布尔值；没有证实正常选择槽和科技的脚本入口。`set_technology` 直接设等级，console `research` 直接完成、`research_on_icon_click` 点击即研究，均不满足正常研究。Play Mode 必须用 GUI 选择后让游戏计时，并读回进行中/完成状态。
2. **National Focus**：`has_completed_focus` 可查完成；`complete_national_focus` 直接完成。没有证实「选中→开始计时」的正常外部 API。Play Mode 用 GUI，当前选择与剩余天数读取列为 UNKNOWN，初期可能用 UI 兜底。
3. **Production**：`add_equipment_production` 明确能新建线，且允许直接指定 `requested_factories`、`progress`、`efficiency`。这**不能证明**与玩家创建/改线及效率损失规则等价。Play Mode 的新建、加减工厂和换装备用 GUI；逐线遥测与效率值列为 UNKNOWN。
4. **Army / Front**：参考项目实做组军、选将、画前线、画进攻线、执行计划的玩家输入；仅第一支集团军、自建 arena 有校准。`num_battle_plans` 等只给摘要，无法重建完整线形。fallback、garrison、naval invasion、paradrop 有旧 Wiki 的 GUI 概念依据，但没有本机实测或参考项目实现，按 GUI 待验证；不得用 `moveunit`/`teleport` 代替。

| Army 子操作 | Play Mode 路径 | 当前证据/限制 |
|---|---|---|
| create army / assign divisions | GUI | R2 组军：选未分配师→绿色 `+`→检查军卡 |
| assign general | GUI | R2 选军→指挥官槽→首个将领；多军/任意将领待验证 |
| frontline / offensive line / execute | GUI | R2 `draw_front`、`draw_offensive`、`activate`；仅 arena |
| fallback line / garrison | GUI，待实机 | W0 旧 Wiki 有界面概念；当前版本手势/校验 UNKNOWN |
| naval invasion / paradrop | GUI，待实机 | W0 旧 Wiki 有界面概念；条件、航程、制海/制空、准备时间校验 UNKNOWN |

## HOI4-AI 可复用与不复用

| 模块 | 判断 | 限制/适配点 |
|---|---|---|
| Rust `desktop-worker` + Python `desktop.py` 协议 | 可作为本地输入/截图底座候选 | Windows 窗口/PID 校验、前台保护、SendInput、释放、watchdog 已实现；需删去/隔离 setup 的 console 输入能力，审计进程/端口、版本和许可；本阶段未运行。 |
| `remote.py`、`Game-Control.ps1` | 可借用设计；按需复用 | 当前偏双机 self-play/arena 启动；本项目先单机，只保留安全附着、报告和明确授权的启动/关闭。 |
| `vision.py` ScreenRules/Observation | 可作 fallback/动作后确认 | 固定分辨率和模板需重新校准；截图不作为主状态源。 |
| `hand.py` ScriptedHand + `scripted.py` Planner | 复用「typed intent→正常 GUI 操作→读回」模式；代码仅局部可移植 | 地图颜色、坐标、首军、arena 国别/州 ID、按钮模板等强耦合，不能原样泛化。 |
| `state_channel.py`、`arena_log.py` | 可复用日志协议/offset/解析思路 | 原码绑定 16 州 arena 和特定国家、装备/法律；不得宣称通用 HOI4 telemetry。`desktop-worker/src/telemetry.rs` 报的是 CPU/内存/GPU/磁盘/网络等主机指标，不是游戏内状态。 |
| PPO、self-play、BC、端到端视觉 policy、视频编码/训练、双机计算 | 当前目标无关 | Phase 1 不研究算法，Phase 2 不引入训练栈。 |

错误恢复方面，worker 有失焦/连接断开释放和 750 ms watchdog；`vision.py` 对分辨率、ROI、模板不匹配显式报错；`ScriptedHand` 在失败时有限重试并返回状态。这些值得迁移，但应把「输入已发送」「UI 显示成功」「Mod 遥测确认生效」分成三种回执，不能把截图变化等同于游戏状态已改变。

## Mod Telemetry 与整体架构建议

**可先做的 Mod Telemetry**：on action 周期/事件采样；通过 scope、trigger、动态变量和临时变量取日期、国力数值、指定科技/国策/法律状态、工厂汇总、装备库存、领土/省份控制、将领和计划摘要；以带版本/日期/国家/序号的 `log` 行写 `game.log`。参考 arena 已实测这条链路。对逐线生产、当前国策进度、完整战线几何、舰队/联队任务等先保留 UNKNOWN，不能用猜测字段填值。Mod 不提供可接受外部任意命令的 scripted effect 通道。

```text
Codex（高层战略意图）
  ↓ typed MCP tools / resource
MCP Server（状态 schema、证据时间戳、动作授权与回执）
  ├─ game.log 增量读取器 ← 只读遥测 Mod（on_actions + log）
  └─ 本地 GUI Executor → Windows worker（窗口绑定、输入、watchdog）→ HOI4
                         ↘ 截图/模板：只用于缺失遥测与动作后确认
```

Play Mode 使用独立的动作白名单和 Mod 包：没有 console key/console 工具、没有发送任意 effect 的入口；只接受玩家等价 GUI intent。Debug Mode 用独立配置/进程/日志和明确标记的场景存档，可用作弊命令造测试场景，其结果不得混入 Play 验收。外部输入须在前台、分辨率/校准匹配后执行；每步记录前态、意图、输入、后态、超时与恢复原因。

## UNKNOWN 与未完成验证

- 在线 Wiki 九类指定页面未逐页复核；Chrome 连接器报 `nodeRepl.fetch request failed`，Playwright Chrome 进程崩溃；直接网页访问遇 401/挑战页。它们不能作为本次已读证据。
- 本机未运行游戏；没有实测 Mod 加载、日志刷新延迟/格式、DLC/版本差异、存档安全、GUI 坐标、焦点切换和现场恢复。参考项目的实机证据仅适用于其 arena 配置。
- 研究槽与具体科技及剩余时间、当前国策与进度、生产线明细/效率、施工队列、完整军队命令树、逐师补给、逐联队/舰队任务和情报行动明细的通用遥测均 UNKNOWN。
- 没有发现可用于 Research/Focus/Production/Army 四系统的正常外部动作 API；这是对所查文件的结论，不是对闭源引擎的不存在证明。
- fallback/garrison/naval invasion/paradrop、任意国家/地图 GUI 方案和动作后遥测闭环均待实机验证。

## Phase 2 建议范围（本阶段未执行）

建议下一阶段只做**最小垂直原型**：固定本机 1.19.3、单机德国 1936、固定分辨率。先做只读 Mod 的日期/PP/研究状态/国策完成状态/工厂总量/装备库存日志，以及增量解析器和字段证据时间戳；再接一个受限 GUI Executor，仅实现「选择一项正常研究」「选择一个正常国策」两项动作和前后态检查。将 Play/Debug 配置、命令白名单、日志与测试存档隔离。验收需实际 Mod 日志、GUI 录像/截图、前后状态三方一致；生产与军队控制留待后续阶段。**不在 Phase 1 开始这些实现。**

## 本阶段文件与检查

- 新增：`reference/HOI4-AI/`（`git clone --depth 1`，固定提交 `73595d38c132d1c2bb10269effe09beb187972a7`；第三方参考源码，未修改）。
- 新增：本报告 `PHASE1_CAPABILITY_INVESTIGATION.md`。无项目代码、MCP、Mod 或 Executor 实现。
- 检查：克隆成功；本机 Steam manifest/launcher 版本与 `documentation/`、`common/` 实例已核对；静态调用链和源码行已抽查。没有运行构建/单测/HOI4 实机测试，本阶段不声称运行验证。
