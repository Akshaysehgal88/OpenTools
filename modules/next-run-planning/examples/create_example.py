"""Generate inspect-first and replay plans with preserved outcome records."""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment_core import fingerprint


def example():
    hypotheses=[{'id':'H1','statement':'The request was not accepted.','basis_ref':'synthetic:timeout has ambiguous acceptance'},
                {'id':'H2','statement':'The request was accepted but did not complete before the deadline.','basis_ref':'synthetic:in-flight path may be blocked'}]
    observation_ids=['scope','acceptance','completion']
    def effects(a,b):
        return [{'hypothesis_id':'H1','assessment':a},{'hypothesis_id':'H2','assessment':b}]
    outcomes=[{'id':'not_accepted','kind':'observation','condition':'Complete correlated request window shows no acceptance',
               'requires':observation_ids,'effects':effects('supported','weakened'),'next_step':'Inspect upstream request/ready arbitration.',
               'evidence_ref':'synthetic:decision before observing outcome'},
              {'id':'accepted_unfinished','kind':'observation','condition':'Correlated acceptance is present; complete response window has no completion by deadline',
               'requires':observation_ids,'effects':effects('weakened','supported'),'next_step':'Inspect the outstanding transaction/grant path.',
               'evidence_ref':'synthetic:decision before observing outcome'},
              {'id':'completed','kind':'observation','condition':'Correlated request completed despite timeout report',
               'requires':observation_ids,'effects':effects('weakened','weakened'),'next_step':'Inspect checker/transaction attribution rather than assuming either explanation.',
               'evidence_ref':'synthetic:decision before observing outcome'}]
    for key,kind,condition,action in [
        ('insufficient','inconclusive','Window, identity or values cannot distinguish acceptance/completion','Locate missing original evidence or repair the minimum observation scope.'),
        ('run_failed','execution_failed','Proposed native execution fails before collecting required data','Retain failure and investigate the execution/collection failure.'),
        ('replay_changed','replay_diverged','Replay differs from the original relevant execution','Retain branch evidence and repair or explicitly scope correspondence.')]:
        outcomes.append({'id':key,'kind':kind,'condition':condition,'requires':[],'effects':effects('unresolved','unresolved'),
                         'next_step':action,'evidence_ref':'synthetic:negative outcome decided in advance'})
    plan={'format':'opentools.experiment-plan.v1','plan_ref':'synthetic:inspect-original-v1','investigation_ref':'synthetic:timeout',
          'original_run_ref':'synthetic:original-run','observation':{'statement':'A single request timed out at the recorded deadline.',
                                                                  'evidence_ref':'synthetic:original timeout log'},
          'question':'Was this request accepted, and did it complete before the timeout?',
          'hypotheses':hypotheses,
          'variables':[{'name':'source execution','role':'fixed','baseline':'synthetic:original-run','proposed':'synthetic:original-run',
                        'evidence_ref':'synthetic:original evidence identity'}],
          'required_observations':[{'id':'scope','description':'Correlate the same request and full request/deadline interval',
                                    'scope':'original transaction/window','attainability_ref':'synthetic:existing full journal inventory'},
                                   {'id':'acceptance','description':'Request-valid/ready acceptance with clock/reset context',
                                    'scope':'original correlated transaction','attainability_ref':'synthetic:existing full journal'},
                                   {'id':'completion','description':'Response/retirement through the recorded deadline',
                                    'scope':'original correlated transaction','attainability_ref':'synthetic:existing full journal'}],
          'outcomes':outcomes,
          'next_action':{'kind':'inspect_existing','summary':'Read the retained original transaction journal before any rerun.',
                         'rationale':'It already covers the required identity, acceptance and completion window.',
                         'alternatives':[{'kind':'propose_run','why_not':'A new simulation would recollect the needed existing facts.',
                                          'evidence_ref':'synthetic:artifact inventory'}],
                         'evidence_ref':'synthetic:available journal metadata'},
          'stopping_condition':'Stop this step after a mapped answer or the precise missing evidence is established.',
          'reproduction':{'kind':'evidence_only','basis_ref':'synthetic:original execution journal','limits':['No new execution or release conclusion.']},
          'prior_search':{'performed':True,'scope_ref':'synthetic:issue run directory','evidence_ref':'synthetic:existing plans/results/artifacts inspected'},
          'unknowns':['The cause of an accepted request remaining unfinished is not yet established.']}
    result={'format':'opentools.experiment-result.v1','result_ref':'synthetic:original-inspection','plan_sha256':fingerprint(plan),
            'state':'observed','actual_route':'inspect_existing',
            'execution':{'attempted':False,'run_ref':None,'exit_code':None,'evidence_ref':'synthetic:read-only inspection, no new simulation'},
            'outcome_id':'accepted_unfinished',
            'actual_variables':[{'name':'source execution','value':'synthetic:original-run','evidence_ref':'synthetic:journal binding'}],
            'observations':[{'id':'scope','value':{'same_request':True,'complete_window':True},'complete':True,'evidence_ref':'synthetic:full journal'},
                            {'id':'acceptance','value':{'accepted':True},'complete':True,'evidence_ref':'synthetic:handshake'},
                            {'id':'completion','value':{'completed_by_deadline':False},'complete':True,'evidence_ref':'synthetic:complete response window'}],
            'correspondence':{'status':'not_applicable','evidence_ref':'synthetic:original evidence, not a replay','limits':['Original record claims remain source-dependent.']},
            'interpretation':'Acceptance is observed without completion by the deadline; inspect the in-flight path next.',
            'remaining_unknowns':['Which upstream control or protocol event blocked completion?'],'cost_observations':[]}
    replay=copy.deepcopy(plan)
    replay['plan_ref']='synthetic:observation-replay-v1'
    replay['next_action']={'kind':'propose_run','summary':'Propose one observation-only replay covering the correlated request/deadline.',
                           'rationale':'This separate example assumes no retained record covers the required interval.',
                           'alternatives':[{'kind':'inspect_existing','why_not':'Only an inadequate late trace is retained in this scenario.',
                                            'evidence_ref':'synthetic:late-window artifact inspection'}],
                           'evidence_ref':'synthetic:minimum attainable handshake collection'}
    replay['variables']=[{'name':'stimulus input','role':'fixed','baseline':'synthetic:input-A','proposed':'synthetic:input-A','evidence_ref':'synthetic:input identity'},
                         {'name':'observation','role':'intended','baseline':'late window','proposed':'correlated request through deadline',
                          'evidence_ref':'synthetic:known trace capability and window'}]
    replay['reproduction']={'kind':'original_reproduction','basis_ref':'synthetic:original binary/input/source context',
                            'limits':['Actual replay correspondence must be checked; same seed alone is insufficient.']}
    unexecuted=copy.deepcopy(result)
    unexecuted.update(result_ref='synthetic:unexecuted-replay',plan_sha256=fingerprint(replay),state='not_executed',actual_route='propose_run',
                       outcome_id=None,observations=[],actual_variables=[],interpretation=None,remaining_unknowns=['This is a proposal only.'])
    unexecuted['execution']={'attempted':False,'run_ref':None,'exit_code':None,'evidence_ref':None}
    unexecuted['correspondence']={'status':'unknown','evidence_ref':None,'limits':['No replay executed.']}
    return plan,result,replay,unexecuted


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
    out=Path(args.directory);out.mkdir(exist_ok=False)
    values=example()
    extra={}
    late=copy.deepcopy(values[0]);late['plan_ref']='synthetic:inspect-late-trace-v1'
    late['next_action']['summary']='Inspect the retained late trace and establish its actual evidential boundary.'
    late['next_action']['rationale']='First determine whether this existing artifact can answer the question.'
    inconclusive=copy.deepcopy(values[1]);inconclusive.update(result_ref='synthetic:late-trace-inspection',plan_sha256=fingerprint(late),
           state='inconclusive',outcome_id='insufficient',interpretation='The request predates this trace; neither explanation is resolved.')
    inconclusive['observations']=[{'id':'scope','value':{'available':[220,250],'needed_start':170},'complete':False,'evidence_ref':'synthetic:late trace bounds'},
                                {'id':'acceptance','value':None,'complete':False,'evidence_ref':'synthetic:acceptance not in this window'}]
    divergent_plan=copy.deepcopy(values[2]);divergent_plan['plan_ref']='synthetic:replay-with-uncontrolled-schedule-v1'
    divergent_plan['variables'].append({'name':'external schedule','role':'uncontrolled','baseline':None,'proposed':None,'evidence_ref':'synthetic:schedule capture unavailable'})
    divergent=copy.deepcopy(values[1]);divergent.update(result_ref='synthetic:divergent-replay',plan_sha256=fingerprint(divergent_plan),
           state='diverged',actual_route='propose_run',outcome_id='replay_changed',interpretation='Relevant replay observations differ; keep original hypotheses unresolved.')
    divergent['execution']={'attempted':True,'run_ref':'synthetic:replay-run','exit_code':0,'evidence_ref':'synthetic:completed different replay'}
    divergent['actual_variables']=[{'name':v['name'],'value':copy.deepcopy(v['proposed']),'evidence_ref':'synthetic:actual capture'}
                                 for v in divergent_plan['variables'] if v['role']!='uncontrolled']
    divergent['correspondence']={'status':'diverged','evidence_ref':'synthetic:observed sequence differs','limits':['Fixed input/seed did not establish schedule equivalence.']}
    extra.update({'late-plan':late,'inconclusive-result':inconclusive,'divergent-plan':divergent_plan,'divergent-result':divergent})
    for name,value in [*zip(('inspect-plan','inspect-result','replay-plan','unexecuted-result'),values),*extra.items()]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
