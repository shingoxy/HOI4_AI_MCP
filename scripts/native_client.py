"""Bounded semantic SDK client with no Computer Use pump or model dependency."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hoi4_operator.executor.guard import WindowsProbe
from hoi4_operator.executor.native_win32 import WindowsDesktop
from hoi4_operator.executor.windows_native import WindowsNativeBackend
from hoi4_operator.executor.ui_state import UIState
from hoi4_operator.executor.templates import Templates
from hoi4_operator.executor.production_lines_ui import ProductionLinesUI
from hoi4_operator.executor.non_military_layout import PRODUCTION as LAYOUT
from hoi4_operator.executor.guard import ActionError
from hoi4_operator.actions.production import signature
from hoi4_operator.actions.construction import validate as validate_construction, order as construction_order
from hoi4_operator.actions.military import expected_land, validate_transition, order_signature
from copy import deepcopy


def resolve(value, snapshot):
    if isinstance(value, str) and value.startswith("$snapshot."):
        current = snapshot
        for field in value.split(".")[1:]:
            current = current[int(field)] if isinstance(current, list) else current[field]
        return current
    if isinstance(value, dict): return {key: resolve(item, snapshot) for key, item in value.items()}
    if isinstance(value, list): return [resolve(item, snapshot) for item in value]
    return value


async def run(args):
    args.output = args.output.resolve()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or not 1 <= len(plan) <= 10:
        raise ValueError("plan must contain 1..10 semantic steps")
    result = {"source": "LIVE HOI4 / official SDK stdio / WindowsNativeBackend",
              "computer_use_pump": "OFF", "computer_use_required": False,
              "model_client": "NONE; Codex selected the bounded semantic plan", "actions": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    probe, desktop = WindowsProbe(), WindowsDesktop(args.window)
    pid = probe.pid(args.window)
    def capture(label):
        reason = probe.check(args.window, pid)
        if reason:
            return {"status": "unavailable", "reason": reason}
        geometry = desktop.geometry()
        rgb = desktop.capture(geometry)
        reason = probe.check(args.window, pid)
        if reason:
            return {"status": "unavailable", "reason": reason}
        path = args.output.parent / "captures" / f"{args.output.stem}-{label}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb).save(path)
        return {"status": "captured", "path": str(path),
                "size": [geometry.width, geometry.height]}
    transport = StdioServerParameters(command=sys.executable, args=[str(ROOT / "scripts/run_mcp.py"),
        "--gui-window", str(args.window), "--backend", "native", "--capture-space", args.capture_space,
        "--non-military", "--military"])
    async with Client(transport, read_timeout_seconds=180) as client:
        capabilities = json.loads((await client.read_resource("hoi4://telemetry/capabilities")).contents[0].text)
        result["capabilities"] = capabilities
        result["tools"] = [tool.name for tool in (await client.list_tools()).tools]
        if capabilities["computer_use_required"] or capabilities["input_backend"] != "native":
            raise RuntimeError("independence_precheck_failed")
        save()
        telemetry_only = all(step["action"] in {"get_summary", "get_politics", "get_industry",
            "get_research", "get_focus", "get_changes", "get_diagnostics"} for step in plan)
        summary = (await client.call_tool("get_summary")).structured_content
        if not telemetry_only:
            deadline = time.monotonic()+90
            while time.monotonic() < deadline:
                summary = (await client.call_tool("get_summary")).structured_content
                if summary and summary["status"] == "fresh" and summary["freshness_basis"] == "frame_received_at":
                    break
                await asyncio.sleep(.25)
            else:
                result["harness_stop"] = "telemetry_not_fresh"
                save()
                return
        result["telemetry_only"] = telemetry_only
        result["before_telemetry"] = summary
        if args.fresh_signal:
            args.fresh_signal.write_text(json.dumps(summary), encoding="utf-8")
        snapshot = None
        for index, step in enumerate(plan):
            arguments = resolve(step.get("arguments", {}), snapshot)
            audit_directory = ROOT/"artifacts/phase5/runtime/native-audit"
            previous_audits = set(audit_directory.glob("*.json"))
            before = capture(f"{index}-before")
            reply = await client.call_tool(step["action"], arguments)
            action_result = reply.structured_content or {"status": "rejected", "reason": "mcp_tool_error"}
            native_audits = [json.loads(path.read_text(encoding="utf-8")) for path in
                             sorted(set(audit_directory.glob("*.json"))-previous_audits)]
            result["actions"].append({"action": step["action"], "arguments": arguments,
                                      "result": action_result, "before_capture": before,
                                      "after_capture": capture(f"{index}-after"), "native_audit": native_audits})
            save()  # Persist before any next step; never resubmit an uncertain action.
            print(json.dumps({"action": step["action"], "status": action_result.get("status"),
                              "reason": action_result.get("reason"),
                              "duration_ms": action_result.get("duration_ms")}), flush=True)
            status = action_result.get("status")
            if (status in {"rejected", "failed", "timed_out", "uncertain"} or
                    status not in step.get("expected", ["confirmed", "already_satisfied"])):
                result["harness_stop"] = "action_not_confirmed"
                save()
                return
            snapshot = action_result.get("after", action_result)
        if args.production_readback_of:
            original = json.loads(args.production_readback_of.read_text(encoding="utf-8"))
            submitted = original["actions"][-1]
            if (submitted["action"] != "set_production_factory_count" or
                    not submitted["result"].get("mutation_submitted") or
                    sum(e["op"] == "semantic_commit" for a in submitted["native_audit"] for e in a["events"]) != 1):
                raise ValueError("readback_requires_exactly_one_original_submission")
            expected = deepcopy(original["actions"][0]["result"])
            expected["lines"][0]["factories"] = submitted["arguments"]["factories"]
            expected["assigned_military_factories"] += 1
            audit_directory = ROOT/"artifacts/phase5/runtime/native-audit"
            previous_audits = set(audit_directory.glob('*.json'))
            backend = WindowsNativeBackend(args.window, pid, probe=probe, audit_directory=audit_directory)
            base = UIState(backend, Templates(ROOT/'artifacts/phase3a/templates'), Templates(ROOT/'artifacts/phase5/templates'))
            ui = ProductionLinesUI(base, Templates(ROOT/'artifacts/phase3/templates'), ROOT/'artifacts/phase5/templates/production')
            readback = {"action": "set_production_factory_count", "original_action_id": submitted['result']['action_id'],
                        "mutation_submissions": 1, "new_mutation_submissions": 0, "status": "failed", "pump": "OFF"}
            started = time.monotonic()
            try:
                backend.begin(15)
                observations = []
                for _ in range(2):
                    view = ui.read(ui.open())
                    if signature(view) != signature(expected) or view['assigned_military_factories'] != expected['assigned_military_factories']:
                        raise ValueError('factory_transition_mismatch')
                    backend.click((LAYOUT['fold_x'], LAYOUT['first_top']+LAYOUT['fold_y_offset']))
                    base.capture()
                    backend.click(LAYOUT['neutral'])
                    deadline = time.monotonic()+2
                    attempts = 0
                    while True:
                        attempts += 1
                        try:
                            grid = ui.grid_count(base.capture(), LAYOUT['first_top'])
                            break
                        except ActionError as exc:
                            if exc.reason != 'readback_failed' or time.monotonic() >= deadline:
                                raise
                            time.sleep(.2)  # Reobserve animated cells; no second input.
                    if grid != submitted['arguments']['factories']:
                        raise ValueError('factory_grid_mismatch')
                    observations.append({'view': view, 'grid_count': grid, 'grid_capture_attempts': attempts})
                readback.update(status='confirmed', readback_source='GUI numeric AND 15-cell grid AND global total; twice', observations=observations)
            except Exception as exc:
                readback['reason'] = str(exc)
            finally:
                backend.close()
                readback['duration_ms'] = round((time.monotonic()-started)*1000)
                readback['native_audit'] = [json.loads(p.read_text(encoding='utf-8')) for p in
                                            sorted(set(audit_directory.glob('*.json'))-previous_audits)]
                readback['after_capture'] = capture('production-readback')
                result['production_readback'] = readback
                save()
            if readback['status'] != 'confirmed':
                result['harness_stop'] = 'readback_not_confirmed'
                save()
                return
        if args.construction_readback_of:
            original=json.loads(args.construction_readback_of.read_text(encoding='utf-8'))['actions'][-1]
            if original['action']!='build' or not original['result'].get('mutation_submitted'):
                raise ValueError('construction_readback_requires_original_submission')
            views=[a['result'] for a in result['actions'] if a['action']=='get_construction']
            if len(views)!=2 or construction_order(views[0])!=construction_order(views[1]):
                raise ValueError('construction_repeated_readback_mismatch')
            if original['arguments'].get('count',1)!=1:
                raise ValueError('unsupported_construction_readback_count')
            diff=validate_construction(original['result']['before'],views[-1],'build',
                                      state_id=original['arguments']['state_id'],building_type=original['arguments']['building_type'])
            result['construction_readback']={'status':'confirmed','action':'build',
                'original_action_id':original['result']['action_id'],'mutation_submissions':1,'new_mutation_submissions':0,
                'duration_ms':sum(a['result']['duration_ms'] for a in result['actions']),
                'readback_source':'GUI complete queue, state/building identity and exact count; two SDK getters',
                'diff':diff,'pump':'OFF'}
            save()
        if args.army_readback_of:
            original=json.loads(args.army_readback_of.read_text(encoding='utf-8'))['actions'][-1]
            if original['action'] not in {'create_army','assign_divisions'} or not original['result'].get('mutation_submitted'):
                raise ValueError('army_readback_requires_original_submission')
            views=[a['result'] for a in result['actions'] if a['action']=='get_divisions']
            before=original['result']['before']
            if original['action']=='create_army':
                division=before['divisions'][0]
            else:
                preceding=json.loads(args.army_readback_of.read_text(encoding='utf-8'))['actions'][0]['result']
                division=next(d for d in preceding['divisions'] if d['division_id']==original['arguments']['division_ids'][0])
            expected=expected_land(before,original['action'],division=division)
            if len(views)!=2:
                raise ValueError('army_readback_requires_two_observations')
            for view in views:
                validate_transition(view,expected)
            result['army_readback']={'status':'confirmed','action':original['action'],'original_action_id':original['result']['action_id'],
                'mutation_submissions':1,'new_mutation_submissions':0,'pump':'OFF',
                'duration_ms':sum(a['result']['duration_ms'] for a in result['actions']),
                'readback_source':'GUI known three divisions, unique first army, exact membership transition and no general; twice'}
            save()
        if args.frontline_readback_of:
            original=json.loads(args.frontline_readback_of.read_text(encoding='utf-8'))['actions'][-1]
            if original['action']!='create_frontline' or not original['result'].get('mutation_submitted'):
                raise ValueError('frontline_readback_requires_original_submission')
            if sum(e['op']=='semantic_commit' for t in original['native_audit'] for e in t['events'])!=1:
                raise ValueError('frontline_readback_requires_exactly_one_submission')
            expected=deepcopy(original['result']['before'])
            expected['fronts'].append({'target_id':original['arguments']['target_id'],'type':'frontline',
                'army_name':expected['armies'][0]['name']})
            expected.update(operation_name='白色方案',plan_active=False)
            views=[a['result'] for a in result['actions'] if a['action']=='get_fronts']
            if len(views)!=2 or any(order_signature(v)!=order_signature(expected) for v in views):
                raise ValueError('frontline_repeated_transition_mismatch')
            result['frontline_readback']={'status':'confirmed','action':'create_frontline',
                'original_action_id':original['result']['action_id'],'mutation_submissions':1,'new_mutation_submissions':0,
                'duration_ms':sum(a['result']['duration_ms'] for a in result['actions']),
                'readback_source':'GUI exact army/divisions, three border segments, complete viewport order mask, operation name and stopped plan; twice','pump':'OFF'}
            save()
        if args.offensive_readback_of:
            original=json.loads(args.offensive_readback_of.read_text(encoding='utf-8'))['actions'][-1]
            if original['action']!='create_offensive_line' or not original['result'].get('mutation_submitted'):
                raise ValueError('offensive_readback_requires_original_submission')
            if sum(e['op']=='semantic_commit' for t in original['native_audit'] for e in t['events'])!=1:
                raise ValueError('offensive_readback_requires_exactly_one_submission')
            views=[a['result'] for a in result['actions'] if a['action']=='get_fronts']
            expected=original['result']['before']
            if len(views)!=1 or not views[0].get('ui_confirmation',{}).get('same_front_and_offensive_signature'):
                raise ValueError('offensive_readback_requires_repeated_full_order_getter')
            for view in views:
                orders=view['offensive_orders']
                if (order_signature(view)!=order_signature(expected) or len(orders)!=1 or
                    orders[0]['target_id']!=original['arguments']['target'] or
                    orders[0]['front_target_id']!='GER_POL_mainland' or
                    orders[0]['army_name']!=expected['armies'][0]['name']):
                    raise ValueError('offensive_repeated_transition_mismatch')
            result['offensive_readback']={'status':'confirmed','action':'create_offensive_line',
                'original_action_id':original['result']['action_id'],'mutation_submissions':1,'new_mutation_submissions':0,
                'duration_ms':sum(a['result']['duration_ms'] for a in result['actions']),
                'readback_source':'GUI same army/front, unique expected offensive direction/target, complete viewport mask and positive order parts; twice','pump':'OFF'}
            save()
        result["after_telemetry"] = (await client.call_tool("get_summary")).structured_content
        result["harness_status"] = "completed"
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-space", choices=("physical", "legacy"), default="physical")
    parser.add_argument("--fresh-signal", type=Path)
    parser.add_argument("--production-readback-of", type=Path)
    parser.add_argument("--construction-readback-of", type=Path)
    parser.add_argument("--army-readback-of", type=Path)
    parser.add_argument("--frontline-readback-of", type=Path)
    parser.add_argument("--offensive-readback-of", type=Path)
    asyncio.run(run(parser.parse_args()))
