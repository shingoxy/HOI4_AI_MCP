"""Read persisted native runs only; never operates the game or decides actions."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
report={}
for name in ('construction-single-1','scripted-days30-1'):
    folder=ROOT/name
    if not (folder/'summary.json').exists():continue
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    relevant=[row for row in events if row['event'] in {
        'decision','action','result','operator_proof','single_gate','game_time','time_safety_stop',
        'fresh_bootstrap','post_action_fresh_bootstrap','shutdown','host_error'}]
    assessment=dict(summary=summary,evidence=relevant)
    failures=[]
    for path in (folder/'native-audit').glob('time-failure-*/failure.json'):
        item=json.loads(path.read_text(encoding='utf-8'))
        failures.append(dict(path=str(path.relative_to(ROOT)),reason=item['reason'],
            captured_at=item['captured_at'],exact_rgb_available=item['exact_rgb_available'],
            modal=item['modal'],ownership=item['ownership'],
            ownership_after_failure=item.get('ownership_after_failure'),
            images_present={name:(path.parent/(name+'.png')).is_file() for name in ('physical','clock','modal','menu')}))
    assessment['time_failures']=sorted(failures,key=lambda item:item['captured_at'])
    (folder/'assessment.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2),encoding='utf-8')
    report[name]=dict(summary=summary,events=[row for row in relevant if row['event'] in {'decision','result','single_gate'}],
        time_failures=assessment['time_failures'])
print(json.dumps(report,ensure_ascii=False,indent=2))
