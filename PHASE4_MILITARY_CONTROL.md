# Phase 4 — Military Control

更新日期：2026-10-05。状态：**COMPLETE / OFFLINE TESTED / LIMITED LIVE VERIFIED**。Army、Frontline、Plan、单师 Supply、有限 Air 和 Navy 观察的既有证据保留；最后的 completion gate `create_offensive_line ×2 confirmed` 已通过两个独立 SDK 会话完成，完整回归通过。Phase 3 提交 `2b1e1f3` 保留，不进入 Phase 5、不创建 Phase 4 子编号。验收后按操作者请求进行 Git 提交 / push，原始验收快照不改写。

## 2026-10-05：2048×1280 进攻线收口

本轮只新增进攻线所需的 profile、选中 Army / Front 观察、专用订单 reader 和语义管线，没有重做既有军事模块或右拖原语。现场保留全屏 2560×1600 / UI scale 1.0，Computer Use capture 和 Win32 GetClientRect 均为 2048×1280；没有改 OS / 游戏显示设置或重启。

私有 [MapProfile](src/hoi4_operator/executor/map_profile.py) 记录 capture_width / capture_height / ui_scale / map_mode / camera_anchor_set / supported_targets / template_set。按实际 capture 精确宽高选择，再由相应模板确认 camera 和 land 模式；scale 是校准元数据，没有独立运行时数值读数。原 `GER_1936_2560x1080` 保留原 Amsterdam / Warsaw / Copenhagen 锚点与其他军事路径。新 `GER_1936_2048x1280` 用真实截图独立校准 **Amsterdam / Copenhagen / Königsberg** 三锚点，只观察第1集团军 / 单个 1. Panzer-Division / 无将领和进攻线所需 Front / Order，不启用其他旧尺寸军事 mutation。未知尺寸拒绝 unsupported_resolution，任一新锚点不匹配拒绝 map_target_unresolved，没有缩放旧坐标。模板见 [新 manifest](artifacts/phase4/offensive2048/templates/manifest.json)，由 [build_offensive_templates.py](scripts/build_offensive_templates.py) 重建。

Agent 接口仍为 `create_offensive_line(army_id, target)`；profile、线段、按钮和模板留在 executor 内部。两个独立会话的 session_id 不同，均从校准视口无进攻线开始：

| 语义目标 | 前线与方向 | 独立 SDK 结果 | ms：导航 / 提交 / 回读 / 确认 / 总计 |
|---|---|---|---|
| `GER_POL_mainland_Poznan_east` | 德波本土前线，波兹南以东方向 | [confirmed](artifacts/phase4/offensive2048/sdk-poz-attempt3.json) | 1969 / 1094 / 1906 / 969 / **5938** |
| `GER_POL_mainland_Poland_north_east` | 同一本土前线，波兰东北的另一目标段 | [confirmed](artifacts/phase4/offensive2048/sdk-north-east-result.json) | 1922 / 1094 / 1750 / 1172 / **5938** |

各会话先官方 SDK get_fronts 刷新 Army / Front snapshots，分别耗时 2531 / 2109 ms。每个进攻线动作 **submit_count=1、retry_count=0、mouse_release_confirmed=true**；通过相同 ActionPipeline / NativeRightDragBackend 提交，两次确切回读一致。第一次验收订单经正常 GUI 清除后才开始第二次；人工校准不计入验收。

管线：fresh GER telemetry / action lock → 重复核对 Army / Front / Order 身份、session 和 TTL → 验证三锚点及已有前线 → 解析方向 → 确认绘制图标和绘制说明同时激活 → 提交前再核对快照 → **一次右拖** → release / 稳定等待 → 两次专用订单回读 → confirmed 或 uncertain 并失效快照。释放错误阻止回读；提交后失败不重发。native 仍只负责右拖，其他输入走 Computer Use，无自动激活或启动。

[OffensiveUI](src/hoi4_operator/executor/offensive_ui.py) 独立于 Frontline reader，同时匹配军队标记、起源前线、箭头尖端、目标曲线，并在私有 Poland ROI 双向核对 empty / 单条波兹南方向 / 单条东北方向 mask，允许 2 像素边缘变化及最多 40 像素残差。缺失、错误方向、额外箭头或多个匹配场景拒绝 / uncertain。成功结果均确认 same_army、same_frontline、new_offensive_order、expected_direction_and_region、no_extra_order_in_calibrated_viewport、repeated_readback。视口外、亚像素和遮挡订单 UNKNOWN，不声明完整枚举。

订单为 **GUI_ONLY / session-local order_id / snapshot_version / 120 秒 TTL / identity_signature / stable_game_identity=false**，after 链接同一版本 Army / Front ID。telemetry 只确认国家、日期和 frame_received_at 时效，未扩展军事字段；新 reader 的 plan_active UNKNOWN，没有执行计划或证明作战。

失败证据全部保留：

- [人工启动失败](artifacts/phase4/offensive2048/calibration-startup-failures.json)：bridge timeout / unavailable，未提交。
- [East 校准错误](artifacts/phase4/offensive2048/east_prussia-calibration.json)：实际关联本土起源，不计成功，正常 GUI 清理。东普鲁士进攻线不启用；按授权替代范围使用两个不同本土 semantic target。
- [加号预检拒绝](artifacts/phase4/offensive2048/mainland_north_east-precheck-rejection.json)：添加真实空槽动画 variant；不放宽 Army / Front / 锚点检查。
- [SDK timeout 1](artifacts/phase4/offensive2048/sdk-poz-pre-submit-timeout.json)、[timeout 2](artifacts/phase4/offensive2048/sdk-poz-attempt2.json)：均只调用 get_fronts，未调用 offensive action。daily fresh frame 约每 49 秒到达，短 bridge 生命周期未覆盖等待；连续 bridge 切片解决会话覆盖，未延长 guard / freshness / action timeout。
- 第二次 confirmed 落盘、服务器退出后，额外 pump 启动被自动审批以可能重复提交为由拒绝。直接读取落盘结果和 SDK exit 0，没有绕过或再提交。

完整回归 **295 passed / 10 subtests passed**：原 263 项保留，新增 32 项覆盖 profile 选择与旧 fixture、第三尺寸拒绝、非比例坐标、三个坏/移位锚点、Army/Front/tool、真实拖后非绘制态、语义目标、专用新/错误/额外/模糊订单、一次提交、重复回读、TTL/失效、释放失败/无重试。既有 SDK schema 检查继续拒绝坐标参数。26 项 native safety 测试保留 right-down 后 F12 / 失焦 / timeout、独立释放监视等；这些异常来自离线 fake mouse，本轮 live 只证明两次正常 release。compileall、pip check、文档链接和 diff 检查见 [verification.json](artifacts/phase4/offensive2048/verification.json)。默认 pytest Temp 受限，使用新的仓库内 basetemp 跑同一完整测试集。

结束真实 GUI **1936-01-26 08:00 / paused**，保留第二条验收订单、单师集团军和两条前线，没有执行计划。本轮未保存或读档；10 个存档及 Mod 选择文件哈希一致，无新增存档。证据：[汇总](artifacts/phase4/offensive2048/live-summary-20261005.json)、[最终哈希](artifacts/phase4/offensive2048/final-files.json)、[暂停截图](artifacts/phase4/offensive2048/captures/final-paused.jpg)。SDK 已退出，游戏保持打开，本轮停止。

## 2026-10-04 历史：仅实现原语，尚未收口

已阅读操作者提供的续接范围，未重新实现或重验 Army / Division / General / Frontline / Plan / Supply / Air / Navy observation。当前已安装 Computer Use 的公开 `drag` 仍没有 button 参数，也没有公开 mouse-down / mouse-up。本轮按明确授权，仅参考 `reference/HOI4-AI/crates/desktop-worker/src/main.rs` 中正常鼠标输入映射，新增私有 [right_drag.py](src/hoi4_operator/executor/right_drag.py)。使用公开 [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput) 和 [MOUSEINPUT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput)，未复用参考 worker 的服务或激活能力。

`NativeRightDragBackend` 包在现有 `InputBackend` 后，仅原语 `right_drag(start, end)` 使用原生输入，其他操作仍委托原 Computer Use worker。军事 opt-in runtime 使用相同 guard 和既有 action lock；只接受内部整数线段及既有 2560×1080 capture profile，每次输入前检查，至多一次 right-down，finally 与独立监视尽力释放右键。失焦、F12、deadline、watchdog、游戏退出或错误进程阻止后续输入；release 失败明确抛出并保留 ownership，供 cleanup 再释放。没有自动激活、启动、任意按钮 API 或 Domain Service 中的 vendor 调用。

语义工具签名按本轮要求改为 `create_offensive_line(army_id, target)`，Agent schema 没有坐标或 button。工具仍明确返回 `rejected / map_target_unresolved`：原语就绪不能替代 Army/Front 身份验证、线段解析、工具激活、一次提交和订单重复读回。没有假设一条拖拽即 confirmed，也没有新增通用地图或其他军事功能。

实机发现当前显示与原校准不同：游戏选项及 settings 为 **全屏 2560×1600 / 60Hz / scale 1.0**，Computer Use 截图与原生 GetClientRect 都是 **2048×1280**，camera 也未匹配原 profile。正常 GUI 选项仅列出 1280×720 和 2560×1600，不能选 2560×1080；尝试正常窗口模式后提示“需要重启游戏以使之生效”，已通过 GUI 恢复原显示选项并关闭菜单，没有自行重启游戏或修改 OS 显示设置。截图：[原显示设置](artifacts/phase4/offensive/captures/display-baseline.jpg)、[重启提示](artifacts/phase4/offensive/captures/restart-required.jpg)、[恢复选项](artifacts/phase4/offensive/captures/display-restored.jpg)。恢复只核对这些显示字段，不声明完整 settings 文件字节一致。

一次真实 official SDK stdio 元数据会话发现全部 50 个工具，验证上述两参数 schema 与 `right_drag_backend=WINDOWS_SENDINPUT` 接入。没有启动 GUI pump 或提交军事动作；SDK 元数据接入不计入军令 confirmed。只读原生几何预检返回 `rejected / unsupported_resolution`；当前真实截图的离线 UIState 回放也返回相同拒绝，二者均发生在输入前。证据：[readiness.json](artifacts/phase4/offensive/readiness.json)、[可复现诊断脚本](artifacts/phase4/offensive/check_readiness.py)。`get_summary` 仅读取历史暂停日志，不能证明当前 fresh telemetry。

本轮完整回归 **263 passed / 10 subtests passed（13.87 秒）**，比既有回归新增 26 项 right-drag 测试：单次 down / endpoint / 正常 release、异常、timeout、F12、失焦、独立监视在 native call 停顿时释放、release 失败、窗口尺寸与已按住右键拒绝、Windows ABI / 虚拟桌面映射、SendInput 失败，以及语义接口隔离。全部为 fake mouse 离线验证，不注入 Windows 输入。进攻线管线及其专用 Front/Army/tool/new-order/unexpected-order readback 测试仍待校准后实现，没有把既有前线测试冒称进攻线测试。compileall、pip check、文档链接及 diff 检查通过；详细验证见 [verification.json](artifacts/phase4/offensive/verification.json)。

最终真实截图确认 **1936-01-01 12:00 / paused**，没有推进日期或军令提交，游戏保持打开。本轮基线的 **10 个存档及 1 个 Mod 选择文件** SHA256 均一致；数量与 2026-10-02 的历史 8 个存档不同，未覆盖或删除用户后来文件。证据：[暂停截图](artifacts/phase4/offensive/captures/final-paused.jpg)、[基线哈希](artifacts/phase4/offensive/baseline-files.json)、[最终哈希](artifacts/phase4/offensive/final-files.json)、[本轮汇总](artifacts/phase4/offensive/live-summary-20261004.json)。没有两次真实进攻线成功，阶段继续 IN PROGRESS；下方 25 个动作会话与 47 confirmed 是 2026-10-02 历史结果，本轮未增加 confirmed。

## 范围与结果（既有验收及新增进攻线）

按已确认草案实现军事观察、身份和正常 GUI 动作，复用现有 InputBackend、ActionPipeline、guard 和 MCP stdio。新增 25 个语义工具（12 个观察、13 个动作），MCP v0.7.0 共 50 个工具。最终官方 SDK `list_tools` 已发现全部 50 个；开发期间早期会话分别为 41 / 46 / 48 个，原始列表保留。这不代表逐一执行了 50 个工具，当前聊天新增工具注册仍为 UNKNOWN。

| 模块 | 已实现及实测范围 | 限制 |
|---|---|---|
| Army / Division / General | 第1集团军；1. Infanterie-Division、1. Panzer-Division、10. Infanterie-Division；创建、分配、移除装甲师、任命曼施坦因 | 只观察 30 师中的 3 师；每次分配一个已知师，不支持移除最后一师 |
| Front / Order | 两处德波前线；2026-10-05 新 profile 的两个本土进攻方向 | 固定 profile；订单游戏 ID、完整分配师列表 UNKNOWN；新进攻线只覆盖上述两个方向 |
| Plan | 集团军整体计划执行 / 停止开关，重复确认按钮和已知边界 | 证明开关切换，不证明作战或进攻线执行 |
| Supply | 1. Infanterie-Division tooltip：补给 100%、储备 150% | 军队 / 前线总体补给及其余师 UNKNOWN |
| Air | 第132战斗机联队、勃兰登堡、80/100 战斗机；分配东德意志 region 8；制空开启 / 关闭 | 只观察 15 联队中的 1 个；其他数量 / 任务拒绝；效率与制空效果 UNKNOWN |
| Navy | 德国海军下公海舰队 task force，母港威廉港、停泊状态、12 艘实际舰名 | 只观察 6 支 task force 中的 1 支；海域 ID / 任务 UNKNOWN；两个 mutation 拒绝 |

getter 返回 `complete=false` 和字段来源，不冒称完整枚举。`get_army`、`get_division`、`get_divisions`、`get_air_state` 复用已验证 reader，已做离线测试，但未分别进行独立 SDK 实机调用。将领 ID 与 region 8 是安装文件定义 / 本地化 / GUI 核对后的 derived 身份；其他军事对象没有宣称稳定游戏内部 ID。

## 草案验收与实际次数

只统计真实官方 SDK stdio 的 `confirmed`，人工校准、`already_satisfied`、提交后未确认和离线 mock 均不计入。

| 动作 / 观察 | 草案最低目标 | 实际 confirmed | 平均总延迟 ms | 原始证据 |
|---|---:|---:|---:|---|
| create_army | 1 | 2 | 12742.50 | [Army 1](artifacts/phase4/army-live-1.json)、[Army 7](artifacts/phase4/army-live-7.json) |
| assign_divisions | 2 | 4 | 22711.00 | [Army 3](artifacts/phase4/army-live-3.json)、[Army 4](artifacts/phase4/army-live-4.json)、Army 7 |
| assign_general | 1 | 2 | 17984.50 | Army 1、Army 7 |
| remove_divisions_from_army | 扩展验证 | 1 | 24843.00 | Army 4 |
| create_frontline | 2 | 2 | 32000.00 | [Front 9：东普鲁士](artifacts/phase4/front-live-9.json)、[Front 10：本土](artifacts/phase4/front-live-10.json) |
| create_offensive_line | 2 | **2，已达标** | 5938 | [波兹南以东](artifacts/phase4/offensive2048/sdk-poz-attempt3.json)、[波兰东北](artifacts/phase4/offensive2048/sdk-north-east-result.json)；两个独立 SDK 会话 |
| execute_plan / stop_plan | 各 1 | 各 1 | 34156 / 32250 | Front 9 |
| get_supply_status | 1 | 1 | 8578.00 | [Front 2](artifacts/phase4/front-live-2.json) |
| assign_air_wing | 1 | 2 | 26203.50 | [Air 5](artifacts/phase4/air-navy-live-5.json)、[Air 6](artifacts/phase4/air-navy-live-6.json) |
| set_air_mission | 1 | 3：制空 ×2、关闭 ×1 | 16239.33 | Air 5、Air 6 |
| get_navy_state / get_fleets | 有限 Navy confirmed | 各 2 | 7632.50 / 7867.50 | [Navy 2](artifacts/phase4/navy-live-2.json)、Air 6 |

另有 get_armies ×8、get_generals ×2、get_fronts ×8、get_air_regions ×3、get_air_wings ×3 confirmed。单次结果保留 before / after、语义参数、session/version、身份和地图解析证据、分阶段耗时；所有 `retry_count=0`。Front 9 / 10 是两处分别确认的新建前线，既有线的 `already_satisfied` 未计数。Air 6 完成区域观察 → 联队观察 → 分配 → 开启制空 → 关闭 → Navy 两次观察 → 两项不支持动作拒绝的完整链路。

2026-10-02 历史总计 **25 个 SDK 会话、74 次调用：47 confirmed、18 rejected、5 uncertain、2 timed_out、2 already_satisfied**；confirmed 包含 18 次 mutation 和 29 次观察。25 条非成功结果完整保留，其中 4 条为预期 Navy 不支持拒绝，其余 21 条是实测失败尝试。汇总：[live-summary-20261002.json](artifacts/phase4/live-summary-20261002.json)，生成器：[summarize_phase4.py](scripts/summarize_phase4.py)。2026-10-05 两个成功会话额外 confirmed get_fronts ×2 / offensive line ×2；另两次提交前 timeout 不计成功，分别见上方新证据。

## 既有身份、地图与安全（2560×1080）

Agent 只传语义参数；坐标、模板、HWND/PID、截图 token 和 backend 对象留在 executor 内部。Army / Division / Front / Air / Fleet 共用 session，采用 version、120 秒 TTL 和可见身份签名；刷新后旧 ID 失效。Army 转换比较全部三个已观察师的归属与将领，Air 转换比较姓名、类型、基地、数量、区域和任务。未知身份、非预期变化或不同的重复读数拒绝 / uncertain；后者使 snapshot 失效。

Private MapResolver 校准两处德波边界：三处城市锚点、每目标三段独立边界标记。前线绘制模式隐藏移动计数器，有限模板与有界采样处理边界闪烁，不重复提交。Air 校验三处一致城市锚点，允许读档至多 2 像素共同位移，再读取真正 region 标题；10 像素平移、坏锚点、不同步位移由测试确认拒绝。没有通用投影或 province resolver。模板由 [构建脚本](scripts/build_phase4_templates.py) 从真实截图重建，范围见 [manifest](artifacts/phase4/templates/manifest.json)。

所有 mutation 沿用 fresh GER telemetry → guarded navigation → identity verification → 最多一次提交 → 两次精确 readback，保留六种 ActionStatus。only-hoi4.exe / HWND / PID / foreground / F12 / watchdog / timeout / 30 秒 freshness guard 未放宽；失焦后 executor 不自动拉前台，失败不自动重发军令。操作者明确授权使用已打开窗口及正常 GUI 解除暂停、调速、读档；最小化后人工正常激活属于该授权，未绕过 executor guard。

军事字段来自 `gui`、`derived` 或 `unknown`，既有 telemetry 只交叉检查国家、日期和时效，没有扩展军事 telemetry 或修改 Mod。GUI 确认“未分配 / 无任务 / 无将领”的空值与未观察的 UNKNOWN 分开。没有 console、effect、直接改 save、Mod 选择更改或 native backend 重写。

## 2026-10-02 历史失败与恢复

| 原始会话 | 失败 | 处理与保留限制 |
|---|---|---|
| Army 1 / 3 | 提交后 readback `ui_timeout` | 保存 timed_out；人工重新观察实际状态，未自动重发；后续独立会话确认分配 / 移除 |
| Army 2 / 7，Air 1 / 3 | `telemetry_stale`，含提交后 uncertain | 保留 30 秒 guard；正常推进并等待读档后两条向前日帧，再重新获取身份 |
| Army 4 | 将领 picker `requirements_not_met` | 根据实际已任命状态修正 reader；后续两个 confirmed picker 观察 |
| Army 5 / 6 | 创建前 `identity_mismatch` | 加号动画采用两个真实模板、有限采样；Army 7 确认创建 |
| Front 1，Air 2 | `map_target_unresolved` | 校准绘制态锚点和读档 1 像素位移；仍拒绝任意 camera 漂移 |
| Front 2 / 3 / 4 / 5 | `readback_ambiguous`，包括提交后 uncertain | 绘制模式隐藏计数器，有限边界闪烁模板；重新观察已有线，没有重复新建 |
| Front 6 | Navy 地图模式下 `identity_mismatch` | 显式切换并确认陆军地图模式 |
| Front 7 / 8，Air 4，Navy 1 | 新闻 / 国策弹窗 `modal_blocked` | 停止，人工核对并正常关闭已知弹窗后重新观察；不自动关闭未知弹窗 |
| Air 5 | 自然补员 80→81，关闭任务前 `identity_mismatch` | 保留拒绝及真实 81 架样本；读回原档后 Air 6 确认关闭，不放宽身份 |
| Navy 2 / Air 6 | 区域分配与巡逻各 `unsupported_target` | 共四次预期拒绝，duration 0、无军令提交；保持 PARTIAL |

实测环境：HOI4 1.19.3 / DirectX11 / GER 1936 开局 / base Chinese / Telemetry Mod only / 2560×1080 / scale 1.0。会话自然推进及重复读档覆盖 1936 年 1–5 月，并非全部在 1 月 1 日。实际每日帧日期见汇总；失败会话未取得 after telemetry 时保留 null。人工校准与 SDK 成功次数分开。

## 2026-10-02 历史回归与恢复

全项目 `.venv` pytest **237 passed / 10 subtests passed**；覆盖既有安全 / 非军事路径，以及 session/version/TTL、一次提交、未知身份、精确变化、地图漂移、真实截图和 80→81 拒绝。compileall、pip check、模板重建、文档链接和 `git diff --check` 通过。项目无已有外部 review 脚本，未新增 review 流程。离线测试不替代实机证据，四个只拒绝动作没有实机成功声明。

最后一次受限环境回归因 pytest 临时目录 `WinError 5` 访问拒绝中断；按此前同环境的执行方式重跑，完整 237 项及 10 项子测试通过（8.61 秒），无需修改实现或测试。该环境失败未作为代码通过证据。

最终正常 GUI 读取 `GER_1936_01_01_12.hoi4`，截图确认 **1936-01-01 12:00 / paused**。同一 reader 确认三个已知师均未分配、无集团军卡；第132联队为 80/100、待命、全部任务关闭。8 个原存档（含 autosave）和 Mod 选择 SHA256 均与本轮基线一致。证据：[restoration.json](artifacts/phase4/restoration.json)、[哈希](artifacts/phase4/restoration-hashes.json)、[暂停截图](artifacts/phase4/captures/restoration-paused.jpg)、[陆军截图](artifacts/phase4/captures/restoration-land.jpg)、[空军截图](artifacts/phase4/captures/restoration-air.jpg)。

最终读档后保持暂停，未再推进两条新日帧，因此 post-load telemetry 为 UNKNOWN；较晚日志不代表恢复后的实时状态。SDK / pump 已退出，游戏保持打开。运行时 token、存档备份、逐次临时 capture 和测试目录由 `.gitignore` 排除；实现、测试、校准 fixtures 和结果留在工作区，未提交。

## 完成状态与保留限制

1. 进攻线 ×2 和完整回归已完成；新增独立 Germany 1936 / 2048×1280 profile，不要求更改显示或任意分辨率适配。其他既有成功次数保留，限定 Phase 4 完成。
2. Province movement 缺少 province 身份到 GUI 目标及正常移动订单确认；`move_divisions` 明确拒绝，校准后才可启用。
3. Navy 海域身份 / 任务选择 / 重复读回未校准；两个 mutation 明确拒绝，当前限观察；完整舰队覆盖、补给和效率 UNKNOWN。
4. Air 固定 80/100，自然补员已证实会拒绝；后续需用真实计数样本扩展 reader，保留前后身份验证，不能宣称任意联队或长期运行能力。

第 2–4 项及任意国家 / 分辨率 / 语言 / camera 均为保留限制，不是新增 completion gate，本轮没有扩展。没有进入 Phase 5。
