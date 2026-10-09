# HOI4 AI Operator — Phase 5 最终完整执行计划

继续当前 `HOI4 AI Operator` 项目。

这是 Phase 5 的最终总执行计划。

从这一轮开始，不再要求每完成一个小 Gate 就停止等待新指令。

在安全、授权和现有项目边界内：

> 持续实现 → 测试 → 实机验证 → 修复 → 回归 → 继续下一个 Gate，直到 Phase 5 达到最终完成标准后再停止。

仍然只有：

```text
Phase 1  Capability Investigation      COMPLETE
Phase 2  Telemetry + MCP               COMPLETE
Phase 3  Non-Military GUI Executor     COMPLETE
Phase 4  Military Control              COMPLETE
Phase 5  Independent Agent Runtime     CURRENT
```

不要创建：

- Phase 5A
- Phase 5B
- Phase 5C
- Phase 6

所有剩余工作统一属于 Phase 5。

---

# 0. 开始前必须读取

完整读取：

- `STATUS.md`
- `PHASE5_AGENT_RUNTIME.md`
- `COUNTRY_AUTONOMY_PLAN.md`
- `AGENT_RUNTIME.md`
- `AGENT_API.md`
- `ARCHITECTURE.md`

以及当前实现：

- `ObservationAggregator`
- `ActionCatalog`
- `AgentRuntime`
- `AgentAdapter`
- `ScriptedAgent`
- `CodexAdapter`
- `GameTimeController`
- `NativeRuntimeHost`
- `WindowsNativeBackend`
- `NativeMapState`
- MapProfile / MapResolver
- modal detector
- Construction / Production / Research / Focus readers
- military readers/executors
- time ownership / safe-stop implementation

必须读取最近证据：

```text
artifacts/phase5/time-safety-20261007/
```

特别是：

- Time Safety A
- Time Safety B
- Construction single
- 30-day failed run
- exact time-failure evidence
- final readonly state
- pytest / verification

并检查：

```text
git status
git log
```

---

# 1. 当前已确认基线

以下结果全部保留，不重跑，除非后续回归确实证明相关实现被修改或退化：

## Native backend

```text
seven-action native gate = 7 / 7 confirmed
```

已确认代表动作：

- Research
- National Focus
- Production factory count
- Construction
- Army assignment
- Frontline
- Offensive Line

全部使用：

```text
WindowsNativeBackend
GDI BitBlt
SendInput
Computer Use pump OFF
```

---

## Runtime

已经实现：

- Strategic Observation
- Action Catalog
- AgentRuntime
- ScriptedAgent
- CodexAdapter abstraction
- GameTimeController
- bounded history
- action budget
- circuit breaker
- timeline reset handling

---

## Scripted Agent

已经确认：

```text
single Production mutation = confirmed
7-day runtime stability = confirmed
```

战略覆盖仍有限。

---

## Construction

最新：

```text
Construction single = confirmed
```

不需要再次制造 Construction mutation 来证明旧能力，除非后续代码修改影响该路径。

---

## Time Safety

已确认：

```text
Time Safety A = live confirmed
Time Safety B = live confirmed
Time Safety C = offline confirmed
```

ownership state machine 当前方向正确：

```text
resume confirmed
→ acquire running ownership

pause confirmed
→ release ownership

pause failure
→ retain ownership
```

禁止退回旧的：

```text
finally:
    owns_running = false
```

---

## 当前完整 regression 基线

```text
585 passed / 10 subtests
```

后续任何阶段都不得降低已有测试覆盖或放宽已有阈值来通过实机。

---

# 2. 当前唯一直接 blocker

最新 30-day Scripted run：

```text
failed after 8 game days
```

实际原因：

```text
World News modal
→ normal pause blocked
→ safe stop route unavailable
→ STOP_FAILED_OWNED
```

这不是 ownership state machine 错误。

相反，它证明：

```text
ownership retained correctly
unsafe shutdown reported correctly
```

当前 blocker 是：

```text
KNOWN_BLOCKING_MODAL = world_news
stop_route = null
```

---

# 3. 总体最终目标

Phase 5 最终必须证明：

```text
HOI4 Agent
↓
Strategic Observation
↓
Action Catalog
↓
Agent Decision
↓
Runtime Validation
↓
OperatorAPI
↓
WindowsNativeBackend
↓
Normal HOI4 GUI
↓
Deterministic Readback
↓
Advance Game Time
↓
Repeat Safely
```

而且：

```text
Codex != runtime dependency
Computer Use != runtime dependency
```

Computer Use 可以保留为 optional/debug backend。

但 Phase 5 validated runtime 必须可以完全：

```text
pump OFF
```

运行。

---

# 4. 授权范围

本提示词授权在当前 HOI4 Germany 1936 测试环境中，为完成 Phase 5 实机验收，使用正常 GUI 执行现有已支持和已校准 semantic actions。

允许：

- 正常 GUI 时间推进
- 正常暂停
- 已验证安全 stop-only route
- Research
- National Focus
- Production
- Construction
- 已验证 Laws / Advisor / Trade
- 已验证 Army / Frontline / Offensive Line
- 已验证 Air limited actions
- 正常 GUI 读档恢复明确测试 baseline
- 为测试建立必要但最小的 test preparation

要求：

- test preparation 与 Agent autonomous behavior 分开记录
- preparation 不计 Agent 成绩
- 不覆盖原始失败记录
- 不把人工准备计为 autonomous decision

不允许：

- console
- effect
- memory write
- save file editing
- Cheat
- 任意未验证 native input API
- 修改 Mod 选择
- 自动删除用户存档
- 覆盖用户原始手动存档
- Computer Use fallback
- 模型直接操作鼠标/键盘

如果出现新的、明显不可逆且超出当前测试范围的游戏状态改变，停止该动作，不自行扩大授权解释。

---

# 5. 第一任务：完成 Modal Stop-Only Framework

当前首先解决 World News。

但实现时不要写成：

```text
if World News:
    special hack
```

建立有限、明确、可审计的：

```text
Modal Stop-Only Matrix
```

状态至少：

```text
NO_MODAL

KNOWN_NONBLOCKING_MODAL

KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP

KNOWN_BLOCKING_MODAL_NO_SAFE_STOP

UNKNOWN_MODAL

OVERLAY_STACK
```

---

# 6. World News Safe Stop

只调查：

> 如何在不选择新闻内容、不改变战略状态的情况下安全暂停游戏。

优先验证：

```text
World News active
→ one Escape
→ calibrated game menu
→ game paused
→ World News remains unresolved
```

必须实机证明。

不能因为 Escape 曾经在其他 modal 工作，就直接启用。

---

# 7. World News Stop Route 成功标准

如果启用：

```text
WORLD_NEWS_SAFE_STOP
```

必须证明：

1. 新闻没有被确认。
2. 新闻没有被关闭。
3. 没有选择任何新闻选项。
4. 没有改变战略状态。
5. 只产生 bounded input。
6. menu template 确认。
7. paused deterministic readback 确认。
8. running ownership 正常 release。
9. 关闭 menu 后新闻仍存在。

否则：

```text
world_news.stop_route = none
```

继续 fail closed。

---

# 8. 不要把 stop-only 变成 popup handler

时间安全层只负责：

```text
stop game safely
```

不能负责：

```text
decide popup
```

不要在这一层自动：

- 点 OK
- 关闭新闻
- 选择事件
- 选择国策
- 选择外交事件

事件决策属于后面的 Agent/semantic action 层。

---

# 9. 常见 Modal 最小覆盖

在实际长期运行遇到后，再逐个有限扩展。

优先级：

```text
World News
Research Complete
National Focus Complete
Known Game Menu
Known Information Popups
```

只有真实出现且确实阻塞 Runtime 时才增加。

不要提前穷举所有 HOI4 popup。

---

# 10. Unknown Modal

任何：

```text
UNKNOWN_MODAL
OVERLAY_STACK not explicitly verified
```

默认：

```text
fail closed
```

如果 Runtime owns running：

```text
retain ownership
attempt only verified generic stop route if safe
otherwise:
    STOP_FAILED_OWNED
    circuit breaker
    operator intervention required
```

---

# 11. 所有时间失败必须保存精确证据

任何：

- pause failed
- modal blocked
- clock unreadable
- safe stop failed
- unknown modal
- STOP_FAILED_OWNED

在任何恢复动作前保存：

```text
full physical RGB
clock ROI
modal ROI
menu ROI
UTC timestamp
telemetry state
foreground
HWND
PID
time ownership state
modal classification
candidate stop route
```

later frame 永远不能替代 trigger frame。

---

# 12. Time Safety Live Gate

World News route 实现后做独立实机 Gate：

```text
paused
→ resume
→ World News active
→ normal pause blocked
→ ownership retained
→ verified safe-stop route
→ paused confirmed
→ ownership released
```

必须：

```text
safe_stop_success = true
```

才能进入长期 benchmark。

---

# 13. 新 fresh baseline

Time Safety Gate 通过后：

重新建立完全新的 Runtime baseline：

```text
new NativeRuntimeHost
new telemetry session
new AgentRuntime
new Observation session
new snapshots
new catalog
new timeline triggers

paused confirmed
NO_MODAL
fresh telemetry
```

不要沿用失败 30-day 的运行时状态。

如果当前世界日期已推进过远，可以使用正常 GUI 加载明确测试 baseline。

不能直接修改 save。

---

# 14. 不再重新验证 Construction

当前：

```text
Construction single = confirmed
```

保持该证据。

只要后续代码没有实质修改 Construction selector/executor/readback：

不要为了测试而重复制造 civilian factory。

如果后续真实 Agent 合理选择 Construction，可以正常执行。

---

# 15. Scripted 30-day 最终稳定性 Benchmark

建立新 run_id。

旧失败：

```text
21/30 failed
8/30 failed
```

全部保留。

不要改写为成功。

---

# 16. 30-day Scripted 运行要求

运行：

```text
Germany 1936
30 actual game days
```

必须：

```text
Computer Use pump = OFF
WindowsNativeBackend
ScriptedAgent
```

Agent 自主：

```text
OBSERVE
→ DECIDE
→ VALIDATE
→ EXECUTE / NO-OP
→ VERIFY
→ ADVANCE
→ REPEAT
```

操作者不得：

- 替 Agent 决定战略动作
- 中途替 Agent 执行 action
- 人工帮它选择 Research/Focus/Construction/Production

允许：

- 启动测试
- F12 emergency stop
- 真正产品级无法恢复时安全介入

出现人工安全介入：

run 必须记录，不可声称完全无人干预。

---

# 17. 30-day 必须记录

至少：

```text
run_id
start_date
end_date
actual_game_days
wall_time

observations
decisions
valid_noops

actions
confirmed
already_satisfied
rejected
uncertain
timed_out
backend_errors

timeline_reset
snapshot_invalidation
circuit_breaker

time_ownership_acquired
time_ownership_released
pause_attempts
pause_failures
safe_stop_attempts
safe_stop_successes

modal_seen_by_type
unknown_modal_count

map_ready
map_recoverable
map_recovery_attempted
map_recovery_success
map_unresolved

human_strategic_interventions
operator_safety_interventions
```

---

# 18. 30-day 硬性成功条件

至少：

```text
actual_game_days >= 30

final paused = confirmed

time_ownership_acquired
==
time_ownership_released

STOP_FAILED_OWNED final = false

unsafe_shutdown = 0

operator_safety_interventions = 0

backend crash = 0

unhandled uncertain = 0
```

如果有 rejected：

只要属于正常 fail-closed 且 Runtime 正确重新观察，可以允许。

但不能存在死循环或反复相同 proposal。

---

# 19. 战略覆盖单独评价

不要把：

```text
30 days reached
```

等于：

```text
strategy complete
```

单独评价：

```text
runtime stability
strategy action coverage
```

例如：

```text
Runtime Stability = PASS
Strategy Coverage = LIMITED
```

这是合法结果。

---

# 20. 30-day 通过后，不再增加 Scripted Gate

只要 30-day 满足 Runtime 稳定性要求：

立即进入 Real Codex Agent。

不要继续：

- 60-day Scripted
- 90-day Scripted
- 另一个 Scripted benchmark

除非真实 Codex 暴露 Runtime 问题。

---

# 21. Real Codex Provider

现有：

```text
Codex CLI installed
ChatGPT login confirmed
structured output support confirmed
```

只是 readiness。

必须真正完成：

```text
real model inference
```

---

# 22. Codex Adapter 设计

Codex 只能收到：

```text
Strategic Observation
Action Catalog
Current Goals
Limited Decision History
```

不能收到：

- Screenshot
- Pixel coordinates
- Templates
- HWND
- PID
- SendInput
- GDI internals
- Map pixel positions
- Computer Use

---

# 23. Codex 输出 Contract

要求结构化：

```json
{
  "assessment": "short strategic assessment",
  "goals": [
    "..."
  ],
  "actions": [
    {
      "action": "...",
      "arguments": {}
    }
  ]
}
```

不要请求或保存 hidden chain-of-thought。

只保存：

```text
assessment
brief rationale
goals
selected actions
```

---

# 24. LLM 输出永远不可信

调用链：

```text
Codex proposal
↓
schema validation
↓
Action Catalog validation
↓
target validation
↓
runtime policy
↓
action budget
↓
OperatorAPI
```

不能：

```text
Codex says click
→ click
```

---

# 25. Codex Single Decision Gate

首先只跑：

```text
one fresh strategic observation
→ one real Codex inference
→ validated AgentDecision
```

如果模型返回合法 no-op：

记录。

继续新的战略周期，直到：

```text
至少1次真实 semantic mutation
```

被模型自主提出。

不要人为告诉模型：

```text
“请修改工厂”
```

来凑测试。

---

# 26. Codex Semantic Action Gate

必须取得至少一次：

```text
real Codex inference
→ semantic action
→ Runtime validation
→ OperatorAPI
→ WindowsNativeBackend
→ HOI4 GUI
→ deterministic readback confirmed
```

且：

```text
Computer Use pump = OFF
```

这才算：

```text
REAL_CODEX_SEMANTIC_ACTION_CONFIRMED
```

fake provider 永远不能替代。

---

# 27. Codex Multi-Cycle Gate

Codex single action confirmed 后：

运行：

```text
5 strategic cycles
```

如果很稳定，可扩到：

```text
10 cycles
```

不要求先跑 30 game days。

---

# 28. Codex Multi-Cycle Metrics

记录：

```text
model calls
model latency
tokens input/output if available

schema valid
schema invalid

catalog valid
catalog rejected

valid no-op
confirmed
already_satisfied
rejected
uncertain

duplicate proposals
repeated failed proposals

game days advanced
human intervention
```

---

# 29. Codex Cycle 成功后正式证明

这时允许记录：

```text
Computer Use is optional for the validated Phase 5 semantic-agent runtime.
```

但仍然不能说：

```text
all project functionality is Computer-Use independent
```

---

# 30. 下一步：Pluggable Agent 真正验证

Codex 验证成功后：

不要修改 Operator/Runtime。

只增加 Agent Adapter。

至少接入一个：

```text
非 Codex 模型
```

优先实现通用：

```text
OpenAI-compatible HTTP Adapter
```

支持配置：

```text
base_url
api_key
model
temperature
timeout
```

---

# 31. 第一个非 Codex 模型

根据当前本机已有环境，优先：

```text
local / OpenAI-compatible Qwen
```

或者已有可直接调用的：

```text
DeepSeek
Qwen
Ollama
LM Studio
vLLM
```

不要为了测试安装多个 provider。

只需要选一个最容易真实运行的非 Codex 模型。

---

# 32. 非 Codex 模型 Gate

必须与 Codex 使用完全相同：

```text
Observation
Action Catalog
History
Goals
```

以及同一个：

```text
AgentRuntime
OperatorAPI
WindowsNativeBackend
```

不能给非 Codex 模型减少安全约束。

---

# 33. 非 Codex 最低验收

至少完成：

```text
real model inference
→ valid AgentDecision
→ semantic action
→ native GUI
→ deterministic confirmed
```

然后：

```text
3–5 strategic cycles
```

---

# 34. Pluggable Agent 完成条件

当：

```text
Codex
```

以及至少：

```text
1个非 Codex 模型
```

都能通过同一个：

```text
AgentAdapter contract
```

运行，而且：

```text
Operator
Native Backend
Observation
Action Catalog
Runtime
```

无需修改时，

才可以正式宣称：

```text
Pluggable Agent architecture live verified
```

---

# 35. Germany 1936 180-day Autonomous Target

在两个模型架构验证后，

使用一个首选 Agent 开始最终 Germany 1936 和平期 autonomous benchmark。

目标：

```text
180 game days
```

这不是为了证明“能打赢二战”。

目标是证明：

```text
一个AI可以持续管理德国1936和平期。
```

---

# 36. 180-day 第一版必须覆盖的领域

优先：

## Research

保持所有已知可管理科研槽尽量不空闲。

需要时扩充：

```text
research catalog
```

但只增加 Germany 1936 和平期需要的有限技术。

---

## National Focus

必须能够在当前 Focus 完成后：

```text
发现 focus missing
→ 选择下一个合法 focus
```

增加有限德国1936 focus catalog。

不要一开始覆盖整个国策树。

---

## Construction

需要能够：

```text
queue empty
→ 添加建设
```

第一版以：

```text
civilian_factory
military_factory
```

在有限已校准州为主。

---

## Production

管理有限已知 production lines。

目标：

- 避免长期闲置军工
- 保持已知优先装备产能
- 不反复抖动 factory count

---

## Politics

如果当前已验证法律/顾问能力可安全纳入 Runtime：

逐步开放。

Agent Catalog 必须反映：

```text
available / unsupported / blocked
```

不要一次开放所有政治 UI。

---

## Trade

仅在已验证：

```text
SWE steel
```

范围内需要时启用。

不要假装完整资源市场已支持。

---

# 37. 180-day 暂时不要求

第一版不要求：

- 完整 Army reorganization
- 全德国军队管理
- 战争 AI
- 空军战略
- 海军战略
- Poland campaign
- 任意国家
- 任意 Mod
- 任意分辨率

---

# 38. 180-day Decision Scheduler

不要每一天调用大模型。

采用：

```text
Daily:
deterministic alerts

Weekly:
strategic AI review

Immediate:
important supported event
```

例如：

```text
research complete
focus complete
construction queue empty
production capacity changed
resource shortage
important known modal/event
```

---

# 39. 180-day 成功指标

至少：

```text
actual game days >= 180
```

Runtime：

```text
no unsafe shutdown
no orphaned running ownership
no unhandled uncertain
no infinite action loop
no uncontrolled modal
```

战略：

```text
research idle minimized
focus idle minimized
construction queue maintained
production utilized within known capability
supported resource shortages handled
```

以及：

```text
human strategic intervention = 0
```

允许：

```text
operator safety intervention
```

但如果发生，需要单独记录，且不能宣称 fully unattended。

---

# 40. 不要为了 180-day 无限扩功能

如果某个动作不在当前支持范围：

Action Catalog：

```text
unsupported
```

Agent 必须绕开。

不要每遇到一个未支持功能就重新扩整个 GUI Executor。

只扩：

> Germany 1936 和平期 180 天真正阻塞可玩性的关键动作。

---

# 41. 长期 Event / Modal Policy

长期 benchmark 遇到新的 modal：

首先判断：

```text
只影响 stop safety？
还是需要 strategic decision？
```

如果只阻塞暂停：

增加：

```text
stop-only route
```

如果需要真正做选择：

不要在底层 modal handler 里硬编码战略选择。

应增加：

```text
semantic event observation
+
semantic event action
```

然后交给 Agent。

---

# 42. Strategic Event Contract

如果长期运行确实需要，可增加：

```text
get_pending_events()
```

以及有限：

```text
resolve_event(event_id, option_id)
```

但只有：

- 实际阻塞
- GUI可稳定读取
- 选项 identity 可确定
- 正常 GUI 可提交
- deterministic readback 可确认

才实现。

不要建立任意 popup click API。

---

# 43. Germany 1936 Capability Expansion 原则

任何新增能力必须依次：

```text
Observe
→ Semantic Contract
→ Deterministic Identity
→ Native GUI Executor
→ Readback
→ Offline tests
→ Live single gate
→ Runtime integration
```

不能跳步骤。

---

# 44. Benchmark Comparison

180-day 稳定后，

再用同一个 baseline 对不同 Agent 做比较。

例如：

```text
Codex
Qwen
DeepSeek
```

同样的：

```text
save baseline
Observation
Action Catalog
Runtime policy
Native Backend
```

---

# 45. 多模型比较指标

至少：

```text
180-day completion rate
wall time
model calls
token usage
decision latency

confirmed actions
rejected
uncertain
timeouts

research idle
focus idle
construction idle
unused production capacity

duplicate proposals
unsupported proposals

human intervention
unsafe stop
```

---

# 46. 不允许模型获得不同权限

不能：

```text
Codex 可以截图
Qwen 不可以
```

所有模型必须只通过：

```text
Observation
Action Catalog
AgentRuntime
```

---

# 47. Agent Memory

第一版保持有限 memory：

```text
current goals
last 20 decisions
last 50 action results
major events
recent failures
```

不要无限增长 prompt。

---

# 48. Strategy State

长期运行允许维护显式：

```text
StrategicState
```

例如：

```text
economy priority
research priorities
focus plan
production goals
construction goals
war preparation goals
```

但这是：

```text
agent-readable state
```

而不是隐藏 chain-of-thought。

---

# 49. Decision Audit

保存：

```text
assessment
goals
brief rationale
chosen actions
results
```

不要保存隐藏推理链。

---

# 50. Runtime 恢复

长期 run 必须支持：

```text
process restart
```

至少能够：

```text
reconnect HOI4
read fresh telemetry
discard stale session IDs
rebuild Observation
rebuild Catalog
resume AgentRuntime
```

不要自动继续旧 pending mutation。

---

# 51. Save / Load Timeline Reset

已有 timeline reset 逻辑必须继续：

```text
load/save rollback
→ clear session snapshots
→ clear pending plan
→ clear date triggers
→ retain audit history
```

---

# 52. Phase 5 最终回归要求

最终必须保持：

```text
all previous tests
```

并增加所有新 Runtime / Agent / modal / 180-day harness tests。

任何真实失败不得通过降低阈值、删除测试或改写旧证据解决。

---

# 53. Phase 5 最终完成标准

只有全部满足才可以：

```text
Phase 5 = COMPLETE
```

至少包括：

## Native Independence

```text
WindowsNativeBackend live verified
Computer Use pump OFF
```

---

## Runtime

```text
ObservationAggregator live verified
ActionCatalog live verified
AgentRuntime live verified
GameTimeController safe ownership verified
Modal stop-only framework verified
```

---

## Scripted Stability

```text
30 game days completed safely
```

---

## Real AI

```text
Real Codex inference verified
Real Codex semantic mutation confirmed
Codex multi-cycle verified
```

---

## Pluggability

```text
At least 1 non-Codex real Agent verified
using same AgentAdapter contract
```

---

## Autonomous Country Management

```text
Germany 1936 peaceful autonomous run
meaningful long-duration benchmark
target = 180 game days
```

如果 180 天由于真正不合理的时间成本或外部环境限制未完成：

不得直接宣称它已完成。

必须明确：

```text
Phase 5 runtime COMPLETE
Long-duration country benchmark PARTIAL
```

但优先尝试完成。

---

# 54. Phase 5 最终不要求

即使 Phase 5 COMPLETE，也不要求：

- 赢得二战
- 自动征服波兰
- 完整战争 AI
- 完整 Air
- 完整 Navy
- 任意国家
- 任意分辨率
- 任意语言
- 任意 Mod
- 所有 HOI4 GUI
- 所有 LLM Provider

---

# 55. 最终架构必须满足

```text
Codex ─────┐
Qwen ──────┤
DeepSeek ──┤
Other LLM ─┘
     │
     ▼
AgentAdapter
     │
     ▼
AgentRuntime
     │
     ▼
Observation + ActionCatalog
     │
     ▼
OperatorAPI
     │
     ▼
WindowsNativeBackend
     │
     ▼
HOI4
```

Computer Use：

```text
optional / debug only
```

---

# 56. 代码和文档

持续维护：

```text
STATUS.md
PHASE5_AGENT_RUNTIME.md
COUNTRY_AUTONOMY_PLAN.md
AGENT_RUNTIME.md
AGENT_API.md
ARCHITECTURE.md
```

新增需要时：

```text
BENCHMARK.md
MODEL_ADAPTERS.md
MODAL_MATRIX.md
```

不要创建 Phase 6。

---

# 57. 每个重大 Gate 都必须落盘

即使不中途停止，也要保存 checkpoint。

例如：

```text
world-news-safe-stop/
scripted-days30-final/
codex-single/
codex-multicycle/
second-agent/
germany-180day/
```

每个必须保存：

- summary
- events
- configuration
- environment
- hashes
- metrics
- failure evidence
- verification

之后继续下一 Gate。

---

# 58. 不要因为失败马上停止

与之前不同：

如果遇到的是：

- reader bug
- calibration bug
- modal bug
- Runtime bug
- adapter bug
- recoverable test failure

则：

```text
diagnose
→ preserve failure evidence
→ fix
→ offline regression
→ rerun only affected Gate
→ continue
```

不需要等待新的用户指令。

---

# 59. 只有以下情况才停止并请求操作者

只有真正外部阻塞才停止，例如：

```text
需要新的登录/认证且无法自动完成

需要用户提供 API key

需要重新启动/启动 HOI4 而当前未授权

必须执行新的不可逆游戏行为而超出已授权测试范围

无法安全暂停且需要人工安全接管

F12 被操作者触发

无法访问必须的外部 provider

系统/OS 权限阻止且无法在当前授权范围内解决
```

普通代码 Bug 不属于停止条件。

---

# 60. 安全停机优先级最高

任何时候：

```text
Runtime owns running
```

都不得直接结束进程。

必须：

```text
ensure_game_stopped()
```

或明确：

```text
operator_intervention_required
```

---

# 61. 不自动 commit / push

开发期间不要因为每个 checkpoint 自动 commit。

但 Phase 5 最终完成时：

先执行：

```text
git status --short
```

检查：

- credentials
- tokens
- runtime secrets
- temp captures
- save backups
- generated caches

确保 `.gitignore` 正确。

不要使用无检查的：

```text
git add .
```

优先明确 staging 应提交内容。

除非用户此前明确授权最终 commit / push，否则最终仍不要自动提交远端。

---

# 62. 最终完整验证

完成所有实现后执行：

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q src scripts tests
.venv\Scripts\python.exe -m pip check
git diff --check
```

以及项目现有的：

- template rebuild checks
- document link checks
- benchmark manifest validation
- artifact consistency checks

---

# 63. 最终报告

最终必须输出一个明确摘要：

```text
PHASE 5 STATUS
```

包括：

## Native Backend

- verified actions
- unsupported actions
- Computer Use requirement

## Runtime

- Observation
- Catalog
- Time Safety
- Modal Coverage
- Circuit Breaker

## Agents

- Codex
- non-Codex Agent
- verified adapters

## Benchmarks

- Scripted 30-day
- Codex cycles
- second model cycles
- Germany autonomous duration

## Safety

- unsafe shutdown count
- unresolved ownership count
- human interventions
- console/effect/save mutation

## Tests

- final pytest count
- compileall
- pip check
- diff check

## Remaining limitations

必须区分：

```text
unsupported
partial
unknown
not live verified
```

不要模糊。

---

# 64. 最终停止条件

只有当：

```text
Phase 5 达到最终完成标准
```

或者：

```text
出现无法自行解决的真正外部阻塞
```

才停止。

不要因为：

- 某次测试失败
- 某个 reader bug
- 某个模板失配
- 某个 modal 未覆盖
- 某个 benchmark 第一次失败

就停止等待用户。

这些应由你自行：

```text
诊断
修复
回归
重测
继续
```

---

# 最终任务定义

最终不是：

> 做几个自动化动作。

而是：

> 建立一个独立于 Computer Use、独立于单一 AI 厂商的 HOI4 Agent Runtime，
> 让真实 AI 能够读取结构化游戏状态、做出战略决策、通过 semantic actions 操作正常 HOI4 GUI、确认结果、推进时间、处理常见运行时异常，并持续管理 Germany 1936 的和平期国家运行。

最终架构必须满足：

```text
Agent interchangeable
Runtime deterministic
GUI execution native
Safety fail-closed
Computer Use optional
Strategy autonomous
Evidence auditable
```

完成全部 Phase 5 工作后再停止。