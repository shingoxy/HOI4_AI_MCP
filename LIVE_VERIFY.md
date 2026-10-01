# Phase 2A 实机验收（有空时手工执行）

1. 在 HOI4 launcher **只启用 Codex Read-only Telemetry Mod**，手工进入单人 Vanilla Germany 1936，保持暂停。
2. 在本项目目录运行 `python scripts/check_telemetry.py`。应看到 `log_exists: true`、成对的 BEGIN/END、`latest_state.country: GER` 和空 `parser_errors`。若暂停时没有帧，先推进一天再检查。
3. 运行 2–5 个游戏日后暂停，重复同一命令；确认 `latest_seq`、`latest_game_date` 和政治力前进。存档再读档时也重复检查；如果日期回退且没有开局帧，先推进两个游戏日让缓存确认新时间线。

`cache_freshness` 根据整个 `game.log` 的最后写入时间估计；长时间暂停后显示 `stale` 是正常的，近期其他日志也可能使它偏乐观。诊断命令只读，不会启动游戏或改变 Mod 选择。把两次输出及游戏内日期/大致时间留作 Phase 2A 实机证据。
