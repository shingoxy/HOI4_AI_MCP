"""Private host metrics from completed native traces; never provider input."""
import json
from pathlib import Path


def map_metrics(directory):
    metrics=dict(MAP_READY=0,MAP_RECOVERABLE=0,MAP_UNRESOLVED=0,
                 recovery_attempted=0,recovery_succeeded=0,recovery_failed=0,
                 recovery_duration_ms=0,clock_recovery_count=0)
    for path in Path(directory).glob('*.json'):
        trace=json.loads(path.read_text(encoding='utf-8'))
        for event in trace.get('events',[]):
            if event.get('op')=='map_state' and event.get('state') in metrics:
                metrics[event['state']]+=1
            elif event.get('op')=='map_recovery_started':
                metrics['recovery_attempted']+=1
            elif event.get('op')=='map_recovery':
                metrics['recovery_succeeded' if event['succeeded'] else 'recovery_failed']+=1
                metrics['recovery_duration_ms']+=event['duration_ms']
            elif event.get('op')=='safe_stop_confirmed':
                metrics['clock_recovery_count']+=1
    return dict(**metrics,meaning='Counts of audited native readiness checks; not unique game days.',
                clock_recovery_scope='Confirmed stop-only menu routes; no automatic modal acknowledgement or resume.')
