"""Independent setup never impersonates an Agent or retries a mutation."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phase5_setup',ROOT/'artifacts/phase5/continuation-20261007/prepare_once.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Operator:
    def __init__(self, status='confirmed', count=12, repeated_count=11):
        self.calls, self.status = [], status
        self.before = dict(status='confirmed',grid_verified_positions=[0],
            military_factories=28,assigned_military_factories=22,lines=[dict(equipment='Kar98k',equipment_id='infantry_equipment_1',
                position=0,factories=count,line_id='fresh-id',identity_complete=True,action_supported=True)])
        self.before['lines'].extend(dict(equipment='other-'+str(i),position=i,factories=n)
                                    for i,n in enumerate((2,1,2,2,1,1,1),start=1))
        self.after = deepcopy(self.before)
        self.after['lines'][0]['factories'] = repeated_count
        self.after['assigned_military_factories'] = 21
    def execute(self,name,args=None):
        self.calls.append((name,args))
        if name=='set_production_factory_count':
            assert args==dict(line_id='fresh-id',factories=11)
            return dict(status=self.status,mutation_submitted=True,retry_count=0,action_id='once',duration_ms=10)
        return {**(self.before if len(self.calls)==1 else self.after),'duration_ms':5}


def test_preparation_durable_once_and_independent_getter():
    op, saved = Operator(), []
    def save(stage,result):
        saved.append(stage)
        if stage=='independent_readback': assert saved[-2]=='setter'
    result = module.run_preparation(op,save)
    assert result['status']=='PREPARATION_CONFIRMED'
    assert [c[0] for c in op.calls]==['get_production_lines','set_production_factory_count','get_production_lines']
    assert saved==['before','setter','independent_readback']


@pytest.mark.parametrize('status',['uncertain','timed_out','rejected','failed'])
def test_preparation_never_retries_or_proceeds_after_failure(status):
    op = Operator(status)
    assert module.run_preparation(op,lambda *args:None)['status']=='BLOCKED'
    assert len(op.calls)==2


@pytest.mark.parametrize('count',[10,11,13])
def test_preparation_wrong_initial_count_never_submits(count):
    op = Operator(count=count)
    assert module.run_preparation(op,lambda *args:None)['status']=='BLOCKED'
    assert len(op.calls)==1


def test_preparation_independent_disagreement_does_not_resend():
    op = Operator(repeated_count=12)
    assert module.run_preparation(op,lambda *args:None)['status']=='BLOCKED'
    assert sum(name=='set_production_factory_count' for name,args in op.calls)==1


def test_preparation_ambiguous_equipment_never_submits():
    op = Operator()
    op.before['lines'][1]['equipment_id'] = 'infantry_equipment_1'
    assert module.run_preparation(op,lambda *args:None)['status']=='BLOCKED'
    assert len(op.calls)==1
