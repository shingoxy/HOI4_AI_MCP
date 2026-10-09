"""Finite stop-only policy. A candidate is never permission to send input."""
from enum import StrEnum
import hashlib
import json
import re

import numpy as np
from PIL import Image

from .templates import Templates


class ModalStopState(StrEnum):
    NO_MODAL = 'NO_MODAL'
    KNOWN_NONBLOCKING_MODAL = 'KNOWN_NONBLOCKING_MODAL'
    KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP = 'KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP'
    KNOWN_BLOCKING_MODAL_NO_SAFE_STOP = 'KNOWN_BLOCKING_MODAL_NO_SAFE_STOP'
    UNKNOWN_MODAL = 'UNKNOWN_MODAL'
    OVERLAY_STACK = 'OVERLAY_STACK'


KNOWN = {'clock_menu', 'world_news', 'research_complete', 'focus_completed_popup'}


def stop_policy(scene, names, route):
    if scene in {'NO_MODAL', 'UNKNOWN_MODAL', 'OVERLAY_STACK'}:
        return dict(stop_state=scene,stop_route=None,candidate_stop_route=None)
    if 'clock_menu' in names:
        return dict(stop_state=str(ModalStopState.KNOWN_NONBLOCKING_MODAL),
                    stop_route='menu_pause_readback',candidate_stop_route=None)
    if len(names)!=1 or names[0] not in KNOWN:
        return dict(stop_state=str(ModalStopState.UNKNOWN_MODAL),stop_route=None,candidate_stop_route=None)
    approved=route if route=='escape_to_menu' else None
    return dict(stop_state=str(ModalStopState.KNOWN_BLOCKING_MODAL_WITH_SAFE_STOP if approved else
                              ModalStopState.KNOWN_BLOCKING_MODAL_NO_SAFE_STOP),
                stop_route=approved,candidate_stop_route='escape_to_menu')


class VerifiedModalStops:
    """Load only immutable live proof; match the observed modal identity at runtime."""
    def __init__(self, templates):
        self.templates=templates
        self.identity=Templates(templates.directory/'modal_stop')
        self.records=[]
        self.rejected=[]
        try:
            root=templates.directory.parents[2]
            manifest=json.loads((self.identity.directory/'manifest.json').read_text(encoding='utf-8'))
            if manifest['capture_profile']!='GER_2560x1600_DPI120_PHYSICAL' or manifest['threshold']!=.9:
                return
            records=manifest['routes']
            if not isinstance(records,list) or len(records)>len(KNOWN): return
            for entry in records:
                try:
                    name=entry['modal']
                    if name not in KNOWN-{'clock_menu'} or entry['route']!='escape_to_menu':
                        raise ValueError('unsupported_stop_rule')
                    path=(root/entry['proof']).resolve()
                    if not path.is_relative_to((root/'artifacts/phase5').resolve()):
                        raise ValueError('proof_outside_artifacts')
                    raw=path.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=entry['proof_sha256']:
                        raise ValueError('proof_hash_mismatch')
                    proof=json.loads(raw)
                    if (proof['kind']!='live_windows_native_stop_only' or proof['status']!='confirmed' or
                            proof['backend']!='WindowsNativeBackend' or proof['pump']!='OFF' or
                            proof['capture_profile']!='GER_2560x1600_DPI120_PHYSICAL' or
                            proof['modal']!=name or proof['route']!=entry['route'] or
                            type(proof['semantic_mutations']) is not int or proof['semantic_mutations']!=0 or
                            type(proof['option_inputs']) is not int or proof['option_inputs']!=0 or
                            type(proof['max_stop_inputs_per_ownership']) is not int or proof['max_stop_inputs_per_ownership']!=1 or
                            any(proof[key] is not True for key in ('modal_unresolved_after_menu_exit',
                                'menu_pause_confirmed','ownership_released'))):
                        raise ValueError('live_stop_proof_required')
                    images={}
                    for key in ('before','menu_first','menu_repeat','after_menu_exit'):
                        image=path.parent/proof['images'][key]['file']
                        if not image.resolve().is_relative_to(path.parent): raise ValueError('image_outside_proof')
                        data=image.read_bytes()
                        if hashlib.sha256(data).hexdigest()!=proof['images'][key]['sha256']:
                            raise ValueError('image_hash_mismatch')
                        images[key]=np.asarray(Image.open(image).convert('RGB'))
                        if images[key].shape!=(1600,2560,3): raise ValueError('proof_profile_mismatch')
                    if not all(templates.find(images[key],'clock_menu',(1230,585,1330,620),.9)
                               for key in ('menu_first','menu_repeat')):
                        raise ValueError('menu_readback_missing')
                    box=entry['identity_box']
                    if (len(box)!=4 or any(type(n) is not int for n in box) or
                            not 850<=box[0]<box[2]<=1750 or not 350<=box[1]<box[3]<=1150 or
                            box[2]-box[0]<100 or box[3]-box[1]<24):
                        raise ValueError('invalid_identity_box')
                    x0,y0,x1,y1=box
                    before=images['before'][y0:y1,x0:x1]
                    after=images['after_menu_exit'][y0:y1,x0:x1]
                    if not np.array_equal(before,after): raise ValueError('modal_changed_after_menu_exit')
                    template=entry['identity_template']
                    if not isinstance(template,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,80}',template):
                        raise ValueError('invalid_identity_template')
                    identity_path=self.identity.directory/(template+'.png')
                    identity_bytes=identity_path.read_bytes()
                    if hashlib.sha256(identity_bytes).hexdigest()!=entry['identity_sha256']:
                        raise ValueError('identity_hash_mismatch')
                    identity=np.asarray(Image.open(identity_path).convert('RGB'))
                    if not np.array_equal(before,identity): raise ValueError('modal_identity_missing')
                    self.records.append(entry)
                except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                    self.rejected.append(str(exc))
        except (OSError,ValueError,KeyError,TypeError,IndexError): pass

    def route(self, rgb, names):
        if len(names)!=1: return None
        for entry in self.records:
            if entry['modal']==names[0] and self.identity.find(
                    rgb,entry['identity_template'],entry['identity_box'],.9):
                return entry['route']
        return None
