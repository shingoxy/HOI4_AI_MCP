"""Assemble the checkpoint from persisted evidence; zero GUI calls."""
import hashlib
import json
from pathlib import Path
import re

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
read=lambda path:json.loads(path.read_text(encoding='utf-8'))
tests=(OUT/'pytest-full-2.txt').read_text(encoding='utf-8')
match=re.search(r'(\d+) passed, (\d+) subtests passed in ([\d.]+)s',tests)
assert match and match.group(1)=='585' and match.group(2)=='10'
single=read(OUT/'construction-single-1/summary.json')
days=read(OUT/'scripted-days30-1/summary.json')
checkpoint=read(OUT/'final-readonly-1/final-state.json')
failures=read(OUT/'scripted-days30-1/assessment.json')['time_failures']
assert single['status']=='SINGLE_CYCLE_CONFIRMED' and single['confirmed_mutations']==1
assert days['shutdown']=='unsafe_stop_failed' and days['time_ownership']=='STOP_FAILED_OWNED'
assert len(failures)==5 and all(f['exact_rgb_available'] and all(f['images_present'].values()) for f in failures)
paths=['src/hoi4_operator/game_time.py','src/hoi4_operator/agent_runtime.py',
    'src/hoi4_operator/executor/native_runtime.py','src/hoi4_operator/executor/native_modal.py',
    'src/hoi4_operator/executor/native_map_state.py','src/hoi4_operator/executor/ui_state.py',
    'src/hoi4_operator/executor/native_audit.py','scripts/run_agent_runtime.py','tests/test_time_safety.py',
    'STATUS.md','PHASE5_AGENT_RUNTIME.md','AGENT_RUNTIME.md','AGENT_API.md','ARCHITECTURE.md',
    'COUNTRY_AUTONOMY_PLAN.md']
result=dict(status='BLOCKED_30_DAY_SAFE_STOP_COVERAGE',phase=5,pump='OFF',
    tests=dict(passed=585,subtests=10,duration_seconds=float(match.group(3)),log='pytest-full-2.txt',
        compileall='passed',git_diff_check='passed'),
    time_gates={name:read(OUT/('live-'+name+'-1/result.json')) for name in ('A','B','baseline')},
    time_gate_C='offline_only_31_new_tests',construction_single=single,days30=days,
    first_exact_time_failure=failures[0],exact_time_failure_count=len(failures),
    final_readonly='final-readonly-1/final-state.json',current_pause=checkpoint['paused'],
    operator_safety_intervention_requested_after_run=True,
    operator_pause_confirmation='pending',
    preservation={key:checkpoint[key] for key in ('manual_save_count','manual_saves_unchanged',
        'mod_selection_unchanged','changed','added','removed')},
    real_codex=dict(status='NOT_RUN',reason='prior_30_day_gate_failed',model_calls=0),
    future_plan='COUNTRY_AUTONOMY_PLAN.md',
    source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in paths})
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=result['status'],tests=result['tests'],
    first_exact_time_failure=failures[0],current_pause=checkpoint['paused'],
    preservation=result['preservation'],source_files_hashed=len(paths)),ensure_ascii=False))
