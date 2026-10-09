"""Select this checkpoint's evidence without deleting or rewriting captures."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
inventory = json.loads((OUT / 'evidence-inventory.json').read_text(encoding='utf-8'))
fixtures = json.loads((OUT / 'test-fixtures-read.json').read_text(encoding='utf-8'))
assert fixtures['exit_code'] == 0
records = {r['path']: r for r in inventory['files']}
selected = set(fixtures['files'])
selected.add('artifacts/phase5/runtime-20261006/final-physical.png')

# Keep all structured results (including failures), scripts and small image ROIs.
for name, record in records.items():
    path = Path(name)
    if path.suffix not in {'.png', '.jpg'} or record['bytes'] <= 1024 * 1024:
        selected.add(name)
    if name.startswith('artifacts/phase5/templates/'):
        selected.add(name)
    if name.startswith((
            'artifacts/phase5/time-safety-20261007/',
            'artifacts/phase5/tool-20261007/diagnostic-2/',
            'artifacts/phase5/tool-20261007/selector-native-1/',
            'artifacts/phase5/tool-20261007/safety-stop-1/',
            'artifacts/phase5/tool-20261007/final-readonly-2/',
            'artifacts/phase5/gate-20261006/final/')):
        selected.add(name)
    if name.startswith('artifacts/phase5/gate-20261006/captures/') and (
            path.name.endswith('native.png') or 'after-submit' in path.name):
        selected.add(name)

# Retain source images referenced by calibration manifests.
def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)

for manifest in (ROOT / 'artifacts/phase5/templates').rglob('manifest.json'):
    for value in strings(json.loads(manifest.read_text(encoding='utf-8'))):
        normalized = value.replace('\\', '/')
        candidates = [ROOT / normalized, manifest.parent / normalized,
                      ROOT / 'artifacts/phase5/gate-20261006/captures' / normalized]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_relative_to(ROOT) and resolved.is_file():
                name = resolved.relative_to(ROOT).as_posix()
                if name in records:
                    selected.add(name)

excluded = set(records) - selected
report = {
    'kind': 'checkpoint_staging_selection',
    'selected_files': sorted(selected),
    'selected_mib': round(sum(records[n]['bytes'] for n in selected) / 1048576, 2),
    'local_only_files': sorted(excluded),
    'local_only_mib': round(sum(records[n]['bytes'] for n in excluded) / 1048576, 2),
    'local_only_preserved': True,
    'excluded_test_scratch': True,
}
(OUT / 'staging-selection.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Stage only project code/docs and the explicit evidence selection.
def git_names(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').split('\0')

paths = set(git_names('diff', '--name-only', '-z'))
paths.update(git_names('ls-files', '--others', '--exclude-standard', '-z',
                       '--', 'src', 'scripts', 'tests'))
paths.update(p.name for p in ROOT.glob('*.md'))
paths.update(selected)
paths.update(p.relative_to(ROOT).as_posix() for p in OUT.iterdir() if p.is_file())
paths.add('artifacts/phase5/final-execution-20261007/EXECUTION_PLAN.md')
paths.discard('')
assert all((ROOT / p).resolve().is_relative_to(ROOT) and (ROOT / p).is_file() for p in paths)
cache = ROOT / '.pytest_cache'
cache.mkdir(exist_ok=True)
(cache / 'phase5-stage-paths.nul').write_bytes(
    b'\0'.join((':(literal)' + p).encode('utf-8') for p in sorted(paths)) + b'\0')
print(json.dumps({k: v for k, v in report.items()
                  if k not in {'selected_files', 'local_only_files'}}, ensure_ascii=False))
print(f'Explicit staging paths: {len(paths)}; local-only captures: {len(excluded)}')
