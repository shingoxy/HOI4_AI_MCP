# Phase 5 单轮验收的独立测试准备

2026-10-07。当前状态：**已获用户单独授权，已执行一次并独立 confirmed。** [准备结果](test-preparation-1/summary.json)：12→11 setter 12672 ms，独立 getter 5734 ms，retry 0，最终暂停；不计 Agent 行为。以下保留执行前方案。

ScriptedAgent 原策略保持不变：Kar98k 最终目标为 12。准备操作为操作者的测试夹具调整，单独保存结果，不创建 Agent session，不计入 Agent actions、confirmed mutations、benchmark game days 或自主战略成绩。

1. 附加现有 Germany 测试窗口；确认前台、physical 2560×1600 / DPI120、暂停、pump OFF。遇到失焦/未知窗口/模态/guard 错误停止，不自动启动或切换窗口。
2. 如 telemetry 陈旧，仅通过既有有界正常 GUI 时间控制生成 fresh frame，单独记录 resume / fresh date / pause。取得新的 `get_production_lines` snapshot，要求唯一 infantry_equipment_1 为第一行、12 factories；numeric / 15-cell grid / 八行合计与 header 22/28 全部一致，重复读回。
3. 只调用一次 `OperatorAPI.execute("set_production_factory_count", {"line_id": fresh_line_id, "factories": 11})`，由现有 WindowsNativeBackend 在正常 GUI 完成一个减厂 step。禁止直接点击绕过 Operator、重用旧 line_id、重发 uncertain 或修改 save。
4. 原 setter 必须返回 confirmed，记录 mutation_submitted=true、retry_count=0、numeric/grid/global 三路 proof。先将完整结果落盘，再进行独立 getter。独立 getter 必须 confirmed：同一装备/位置、11 factories、assigned MIL 21/28，其余七行身份/顺序/count 不变。getter 的新 snapshot 不传给后续 Agent session。
5. 恢复安全页面并只读确认暂停。任一 setter/readback/cleanup 失败，停止准备；保留原结果，不用 later readback 改写 uncertain，也不进入 Agent mutation gate。
6. 只有准备独立 confirmed 后，启动全新 ScriptedAgent session，通过 fresh observation / catalog / snapshots 自主选择 11→12。结果和 fresh post-action observation 均满足既有 single gate 才继续 7 天。

单独输出目录为 `artifacts/phase5/continuation-20261007/test-preparation-<attempt>/`；后续 Agent 使用另一新目录。每个 attempt 最多一次 setter。旧 reader-20261006 与 seven-action gate 记录保持不动。

后续 7/30 天结果分别区分运行稳定性、schema-valid decisions、valid no-op、实际 confirmed mutations、策略覆盖和人工干预。游戏日期推进不单独构成自主战略验收成功；没有有意义的受支持目标时明确记录覆盖不足。

此方案仅依赖现有已校准接口，不改目标为11，不降低reader阈值，不扩大GUI范围，不接其他模型，不自动commit/push。
