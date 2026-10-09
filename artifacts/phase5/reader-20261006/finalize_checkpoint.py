"""Persist verification without rewriting historical run results."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from PIL import Image
from hoi4_operator.executor.production_ui import ProductionUI

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

reader = read(OUT/'live-read-5/readback.json')
run = read(OUT/'scripted-single-2/summary.json')
original = read(ROOT/'artifacts/phase5/runtime-20261006/scripted-single-1/summary.json')
final = read(OUT/'final-state.json')
assert reader['status']=='confirmed' and reader['later_readback']==12 and reader['mutation_count']==0
assert reader['original_status']=='uncertain' and original['uncertain']==1
assert run['status']=='SINGLE_GATE_NOT_PASSED' and run['confirmed_mutations']==run['actions']==0
assert run['pump']=='OFF' and run['game_days']==0
assert final['paused'] is True and not any(final[k] for k in ('changed','added','removed'))
log = (OUT/'pytest-final.txt').read_text(encoding='utf-8-sig', errors='replace')
assert '483 passed, 10 subtests passed in 41.41s' in log
checks = {}
for name, command in (
    ('compileall', [sys.executable,'-m','compileall','-q','src','scripts','tests']),
    ('pip_check', [sys.executable,'-m','pip','check']),
    ('diff_check', ['git','diff','--check'])):
    result = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=30)
    checks[name] = dict(exit_code=result.returncode,
        output=(result.stdout+result.stderr).decode('utf-8',errors='replace').strip())
    assert result.returncode==0, name

templates = ROOT/'artifacts/phase5/templates/production'
pair = np.asarray(Image.open(OUT/'compact-0-piece-1.png')) > 0
two = np.asarray(Image.open(templates/'header_digit_2_after_p0.png')) > 0
slash = np.asarray(Image.open(templates/'header_digit_slash_after_p2.png')) > 0
combined = np.zeros((16,13),dtype=bool)
combined[1:1+two.shape[0],:two.shape[1]] |= two
combined[:slash.shape[0],7:7+slash.shape[1]] |= slash
score = float(ProductionUI.glyph_score(combined,pair,True))
assert score==1.0
traces = [read(path) for folder in ('live-read-5/native-audit','scripted-single-2/native-audit','final-native-audit')
          for path in (OUT/folder).glob('*.json')]
assert traces and all(not trace.get('held_input_remaining') for trace in traces)
assert not any(e['op']=='semantic_commit' for t in traces for e in t['events'])
core = next(n for n in ast.parse((ROOT/'src/hoi4_operator/agent_runtime.py').read_text(encoding='utf-8')).body
            if isinstance(n,ast.ClassDef) and n.name=='AgentRuntime')
report = dict(checkpoint='PRODUCTION_READER_CONFIRMED / SINGLE_GATE_NOT_PASSED_ZERO_MUTATIONS',
    tests=dict(passed=483,subtests_passed=10,seconds=41.41,previous_baseline=452,added=31),
    checks=checks, reader=dict(original_status='uncertain',later_readback=12,pump='OFF',mutation_count=0,
        source='live-read-5/readback.json',duration_ms=reader['duration_ms']),
    joined_pair=dict(shape=list(pair.shape),foreground_pixels=int(pair.sum()),
        independent_two_slash_union_IoU=score,threshold_minimum=.84,threshold_margin=.10),
    single=run, protected_files=dict(count=len(final['files']),changed=[],added=[],removed=[]),
    paused=True, native_trace_count=len(traces),semantic_commits=0,held_input_remaining=False,
    runtime_failure_policy_changed=False,
    runtime_core_ast_sha256=hashlib.sha256(ast.dump(core).encode()).hexdigest(),
    pending='Scripted production target rule; no strategy change without answer',
    scripted_7_days='NOT RUN',scripted_30_days='NOT RUN',real_codex='NOT RUN',other_ai='NOT USED',
    commit=False,push=False)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
missing = []
for filename in ('STATUS.md','PHASE5_AGENT_RUNTIME.md','AGENT_RUNTIME.md','AGENT_API.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', (ROOT/filename).read_text(encoding='utf-8')):
        if '://' not in target and not target.startswith('#') and not (ROOT/target.split('#')[0]).exists():
            missing.append([filename,target])
report['document_links'] = dict(missing=missing)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert not missing, missing
print(json.dumps(dict(tests=report['tests'],checks={k:v['exit_code'] for k,v in checks.items()},
    later_readback=12,single=run['status'],native_trace_count=len(traces),document_links_missing=missing)))
