# Phase 3A 复用说明

`executor/templates.py` 的 `TM_CCOEFF_NORMED` 查找方式改编自
`reference/HOI4-AI/src/hoi4_arena/scripted.py` 的 `Planner.find`，选择 MIT 授权。
Copyright (c) 2026 HOI4-AI contributors。完整许可见 `licenses/HOI4-AI-MIT.txt`。

`executor/guard.py` 重新实现 Windows worker 的进程身份、前台保护、F12 和独立 watchdog 设计；
没有复制 worker 的启动、控制台、训练、策略或战场操作功能。
输入与 capture 通过已安装 Computer Use 的公开 `@oai/sky` API，未自建 helper protocol。
参考 `hand.py` 的语义动作与低层输入分离，未导入其依赖链。

`artifacts/phase3a`、`artifacts/phase3b1` 的截图和模板是本机实测界面的裁剪，包含游戏视觉资产，用于本机 PoC 校准和验证。
Phase 3B-1 的数字 masks 还取自本机安装的 HOI4 中文字体；项目不包含完整字体 atlas 或游戏文件。
这些视觉资产不属于 HOI4-AI MIT 授权代码。跨语言、Mod、版本或布局不能沿用实机验证声明。
