"""Separate observed Runtime stability from strategic-action coverage."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from hoi4_operator.agent import ScriptedAgent, validate_decision
from hoi4_operator.action_catalog import build_catalog, VALIDATED_ACTIONS
from hoi4_operator.observation import game_datetime


def assess(directory, requested):
    directory=Path(directory)
    summary=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    events=[json.loads(l) for l in (directory/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    observations=[]
    valid_decisions=noops=0
    current=None
    for event in events:
        if event['event']=='observation':
            current=event['data']
            observations.append(current)
        elif event['event']=='decision':
            catalog=build_catalog(current,VALIDATED_ACTIONS,current['capabilities'])
            decision=validate_decision(event['data'],catalog)
            assert decision==ScriptedAgent().decide(current,catalog,{})
            valid_decisions+=1
            noops+=not decision['actions']
    clocks=[e['data'] for e in events if e['event']=='game_time']
    days=(game_datetime(summary['end_date']).date()-game_datetime(summary['start_date']).date()).days
    strategic=[o for o in observations if o['meta']['detail']=='strategic']
    known_production=[o for o in strategic if o['production']['freshness']=='fresh' and o['production']['data']]
    goals=[dict(date=o['meta']['date'],factories=next(l['factories'] for l in o['production']['data']['lines']
                if l.get('equipment_id')=='infantry_equipment_1')) for o in known_production]
    checks=dict(requested_game_days_completed=days>=requested and summary['game_days']>=requested,
        all_time_steps_confirmed_paused=bool(clocks) and all(c['status']=='confirmed' and c['paused'] for c in clocks),
        all_observations_fresh=bool(observations) and all(o['meta']['fresh'] for o in observations),
        navigation_confirmed=all(e['status'] in ('confirmed','unsupported') for o in observations for e in o['navigation']),
        scripted_decisions_valid=valid_decisions>=2 and valid_decisions==summary['decisions'],
        no_errors=summary['status']=='ACTIVE' and not summary['circuit_breaker'] and
            all(summary[k]==0 for k in ('rejected','uncertain','timed_out','backend_errors','timeline_reset')),
        pump_off=summary['pump']=='OFF')
    result=dict(run_id=summary['run_id'],requested_game_days=requested,actual_game_days=days,
        runtime_stability_confirmed=all(checks.values()),checks=checks,
        valid_decisions=valid_decisions,valid_noops=noops,attempted_actions=summary['actions'],
        confirmed_mutations=summary['confirmed_mutations'],
        operator_strategic_interventions=0,manual_preparation_counted=False,
        strategy_target=12,observed_factory_targets=goals,
        strategic_action_coverage=('supported action attempted but not confirmed' if summary['actions'] else
            'no-op-only; insufficient action-branch coverage') if not summary['confirmed_mutations']
            else 'supported semantic actions exercised; broader strategy remains outside scope',
        full_autonomous_strategy_acceptance=False,
        idle_metrics= {k:v for k,v in summary.items() if k.endswith('_idle_days') or k=='unused_MIL_observations'},
        continuous_research_focus_queue_idle_duration='UNKNOWN: GUI observations are sampled, not continuous',
        no_semantic_mutation_days=days if not summary['mutations_submitted'] else 'not inferred',
        note='Stability requires fresh observations, validated autonomous decisions and confirmed time control, not dates alone.')
    (directory/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    result=assess(sys.argv[1],int(sys.argv[2]))
    print(json.dumps(result,ensure_ascii=False))
    if not result['runtime_stability_confirmed']: raise SystemExit(2)
