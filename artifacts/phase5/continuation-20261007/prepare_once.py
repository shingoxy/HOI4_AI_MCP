"""Separately authorized operator preparation; never an Agent decision."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.executor.native_runtime import NativeRuntimeHost
from hoi4_operator.telemetry.paths import default_log_path


def run_preparation(operator, save):
    before = operator.execute('get_production_lines')
    save('before', before)
    if before['status'] != 'confirmed':
        return dict(status='BLOCKED', reason='preparation_initial_readback_failed', result=before)
    lines = before['lines']
    targets = [l for l in lines if l.get('equipment_id') == 'infantry_equipment_1']
    target = targets[0] if len(targets)==1 else None
    if (len(lines)!=8 or sum(l['factories'] for l in lines)!=22 or
            not target or target['position'] != 0 or target['factories'] != 12 or
            not target.get('identity_complete') or not target.get('action_supported') or
            before['assigned_military_factories'] != 22 or before['military_factories'] != 28 or
            before.get('grid_verified_positions') != [0]):
        return dict(status='BLOCKED', reason='preparation_requires_verified_current_12')
    # One semantic call, with an identity obtained within this preparation.
    result = operator.execute('set_production_factory_count', dict(line_id=target['line_id'],factories=11))
    save('setter', result)  # Durable before a subsequent independent getter.
    if result['status'] != 'confirmed' or result.get('mutation_submitted') is not True or result.get('retry_count') != 0:
        return dict(status='BLOCKED', reason='preparation_setter_not_confirmed', result=result)
    repeated = operator.execute('get_production_lines')
    save('independent_readback', repeated)
    expected = deepcopy(lines)
    expected[0]['factories'] = 11
    signature = lambda value: [(l['equipment'],l['position'],l['factories']) for l in value]
    if (repeated['status'] != 'confirmed' or repeated.get('grid_verified_positions') != [0] or
            signature(repeated.get('lines',[])) != signature(expected) or
            repeated.get('assigned_military_factories') != 21 or repeated.get('military_factories') != 28):
        return dict(status='BLOCKED', reason='preparation_independent_readback_failed', result=repeated)
    return dict(status='PREPARATION_CONFIRMED', before=12, after=11,
                setter_action_id=result['action_id'], setter_duration_ms=result['duration_ms'],
                readback_duration_ms=repeated['duration_ms'],
                readback_source='target numeric AND 15-cell grid AND full-list/global assigned MIL',
                mutation_submitted=True, retry_count=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    summary = dict(pump='OFF', backend='WindowsNativeBackend', role='operator_test_preparation',
        counts_toward_agent_behavior=False, agent=None, strategy_target=12,
        authorization='Explicit user reply 2026-10-07 authorizes this once-only 12-to-11 preparation',
        status='NOT_RUN', stages=[])
    def save(stage, result):
        (args.output/(stage+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        summary['stages'].append(dict(stage=stage,status=result.get('status')))
        (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    host = None
    try:
        host = NativeRuntimeHost(args.window, default_log_path(), ROOT, args.output/'native-audit',
                                ROOT/'artifacts/phase5/gate-20261006/final/native-final-physical.png')
        Image.fromarray(host.preflight()).save(args.output/'preflight.png')
        host.backend.begin(6)
        try:
            if not host.time.gui.is_paused():
                raise ActionError('preparation_requires_paused_start','rejected')
        finally:
            host.backend.end()
        if host.model.summary()['status'] != 'fresh':
            bootstrap = host.time.advance_days(1)
            save('fresh_bootstrap', bootstrap)
            if bootstrap['status'] != 'confirmed':
                raise ActionError('preparation_fresh_bootstrap_failed','rejected')
        summary.update(run_preparation(host.operator,save))
        host.backend.begin(8)
        try:
            host.production.ui.close()
            summary['final_paused'] = host.time.gui.is_paused()
            if summary['final_paused'] is not True:
                summary.update(status='BLOCKED',reason='preparation_final_pause_unconfirmed')
        finally:
            host.backend.end()
    except Exception as exc:
        summary.update(status='BLOCKED',reason=getattr(exc,'reason',type(exc).__name__))
    finally:
        if host:
            try: host.close()
            except Exception as exc:
                summary.update(status='BLOCKED',cleanup_reason=getattr(exc,'reason',type(exc).__name__))
        summary['wall_time_seconds'] = round(time.monotonic()-started,3)
        (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False))
    if summary['status'] != 'PREPARATION_CONFIRMED':
        raise SystemExit(2)


if __name__=='__main__': main()
