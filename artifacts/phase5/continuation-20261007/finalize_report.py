"""Assemble existing evidence; never edits a run result or resumes the game."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
read=lambda path:json.loads(path.read_text(encoding='utf-8'))
prep=read(OUT/'test-preparation-1/summary.json')
single=read(OUT/'scripted-single-1/summary.json')
days7=read(OUT/'scripted-days7-1/assessment.json')
days30=read(OUT/'scripted-days30-1/assessment.json')
raw30=read(OUT/'scripted-days30-1/summary.json')
state=read(OUT/'final-state.json')
pause=read(OUT/'pause-menu-proof.json')
assert prep['status']=='PREPARATION_CONFIRMED' and prep['counts_toward_agent_behavior'] is False
assert single['status']=='SINGLE_CYCLE_CONFIRMED' and single['confirmed_mutations']==single['mutations_submitted']==1
assert days7['runtime_stability_confirmed'] and days7['actual_game_days']==7 and days7['valid_noops']==2
assert not days30['runtime_stability_confirmed'] and days30['actual_game_days']==21
assert raw30['status']=='PLAN_STOPPED' and raw30['rejected']==1 and raw30['mutations_submitted']==0
assert pause['paused'] and not any(state[k] for k in ('changed','added','removed'))
events=[json.loads(l) for l in (OUT/'scripted-days30-1/events.jsonl').read_text(encoding='utf-8').splitlines()]
failed=next(e['data'] for e in events if e['event']=='result')
assert failed['reason']=='map_target_unresolved' and failed['mutation_submitted'] is False and failed['retry_count']==0
traces={}
for folder in ('test-preparation-1','scripted-single-1','scripted-days7-1','scripted-days30-1'):
    data=[read(p) for p in (OUT/folder/'native-audit').glob('*.json')]
    commits=[e for t in data for e in t['events'] if e['op']=='semantic_commit']
    assert data and all(not t.get('held_input_remaining') for t in data)
    expected=1 if folder in ('test-preparation-1','scripted-single-1') else 0
    assert len(commits)==expected
    traces[folder]=dict(native_traces=len(data),semantic_commits=len(commits),held_input_remaining=False)
core=next(n for n in ast.parse((ROOT/'src/hoi4_operator/agent_runtime.py').read_text(encoding='utf-8')).body
          if isinstance(n,ast.ClassDef) and n.name=='AgentRuntime')
core_hash=hashlib.sha256(ast.dump(core).encode()).hexdigest()
old=read(ROOT/'artifacts/phase5/reader-20261006/verification.json')
assert core_hash==old['runtime_core_ast_sha256']
assert '493 passed, 10 subtests passed in 43.01s' in (OUT/'pytest-full1.txt').read_text(encoding='utf-8-sig',errors='replace')
checks={}
for name,cmd in (
    ('compileall',[sys.executable,'-m','compileall','-q','src','scripts','tests']),
    ('pip_check',[sys.executable,'-m','pip','check']),('diff_check',['git','diff','--check'])):
    res=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
    checks[name]=dict(exit_code=res.returncode)
    assert res.returncode==0,name
report=dict(checkpoint='30-DAY GATE STOPPED AT DAY21 / REAL CODEX NOT RUN',
    preparation=prep,scripted_single=single,scripted_days7=days7,scripted_days30=days30,
    failed_action=failed,real_codex=read(OUT/'codex-readiness.json'),native_evidence=traces,
    tests=dict(passed=493,subtests_passed=10,seconds=43.01,previous_baseline=483,added=10),checks=checks,
    runtime_core_ast_sha256=core_hash,runtime_failure_policy_unchanged=True,
    strategy_target=12,pump='OFF',paused=pause['paused'],pause_source=pause['source'],
    original_clock_reader=state['blocker'],protected_files_unchanged=True,
    operator_strategic_interventions=0,save_mutation_by_operator=False,commit=False,push=False,
    next_step='Read-only failed-frame/current viewport investigation in existing native state64 scope; no automatic build replay.')
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
missing=[]
for filename in ('STATUS.md','PHASE5_AGENT_RUNTIME.md','AGENT_RUNTIME.md','AGENT_API.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',(ROOT/filename).read_text(encoding='utf-8')):
        if '://' not in target and not target.startswith('#') and not (ROOT/target.split('#')[0]).exists():
            missing.append([filename,target])
report['document_links']=dict(missing=missing)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert not missing,missing
print(json.dumps(dict(checkpoint=report['checkpoint'],tests=report['tests'],native=traces,
                     paused=True,document_links_missing=missing)))
