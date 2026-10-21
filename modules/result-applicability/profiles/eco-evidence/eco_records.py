"""Original result snapshots and independently requested scope, using parent formats."""
from eco_common import REPORTS,require
from native_eco import projection

def observed_phase(e,kind):
    r=e['reports'][kind];require(r is not None,'Original raw report required to create snapshot')
    if kind=='sta':return {'cases':r['cases'],'clock':r['clock'],'clock_sources':r['sources']}
    samples=r['samples'];return {'reset':samples[0][2],'a':samples[0][3],'b':samples[0][4],'cycles':r['expected'],
                               'clock_pattern':[row[1] for row in samples],'measurement':'logical-half-cycle-counter'}

def fields(e,kind,phase):
    ctx=e['context'];ref=ctx['run_ref']+'/'+('sta.txt' if kind=='sta' else 'clock.stdout.txt');fact=lambda value:{'value':value,'evidence_ref':ref}
    return {'implementation.netlist_sha':fact(e['source_sha256']['design.v']),
            'build.report_producer':fact(e['execution']['binary_sha256'] if kind=='clock' else e['execution']['tools']['openroad_sha256']),
            'models.source_sha':fact(e['source_sha256']['models.sv']),'library.source_sha':fact(e['source_sha256']['cells.lib']),
            'physical_library.source_sha':fact(e['source_sha256']['cells.lef']),
            'checker.source_sha':fact(e['source_sha256']['main.cpp'] if kind=='clock' else e['source_sha256']['export_eco.tcl']),
            'tools.profile':fact(e['execution']['tools']),
            'scope.context':fact({k:ctx[k] for k in ('scope_ref','design_ref','configuration_ref')}),
            'scope.profile':fact('owned-finite-clock-delivery.v1' if kind=='clock' else 'owned-selected-STA-path-presence.v1'),
            'scope.native_projection':fact(projection(e,kind)),'scope.phase_ref':fact(ctx['phase_ref']),'scope.native_phase':fact(phase)}

def snapshot(e,kind):
    require(kind in REPORTS,'Unsupported report type');r=e['reports'][kind];require(r is not None,'Original report unavailable')
    ctx=e['context'];run=ctx['run_ref'];name='sta.txt' if kind=='sta' else 'clock.stdout.txt';ref=run+'/'+name
    status=r['native_status'] if kind=='clock' else 'PATH_RESULT '+r['verdict']+'; selected path presence only'
    return {'format':'opentools.result-snapshot.v1','run_ref':run+'/'+kind,'manifest_ref':run+'/execution.json',
            'execution':{'state':'completed','evidence_ref':run+'/execution.json',
                'command':e['commands']['run'] if kind=='clock' else e['commands']['native'],
                'executable_ref':e['execution']['binary_sha256'] if kind=='clock' else e['execution']['tools']['openroad_sha256'],
                'dependency_capture_complete':True,'dependency_evidence_ref':run+'/graph.txt#qualified-primitive-model-and-declared-phase'},
            'result':{'outcome':r['verdict'].lower(),'native_status':status,'complete':True,'producer_run_ref':run+'/'+kind,
                'evidence_ref':ref,'artifact':{'path':ref,'sha256':e['execution']['artifacts'][name]}},
            'fields':fields(e,kind,observed_phase(e,kind)),
            'provenance':{'profile':'opentools.eco-observation.v1','limits':'Original selected-path presence or finite Boolean clock delivery; not complete ECO equivalence, electrical/timing/route signoff or authenticated approval.'}}

def request(e,kind,policy):
    wanted=fields(e,kind,policy['required_phase'][kind])
    return {'format':'opentools.result-request.v1','claim_id':policy['claim_id']+'/'+kind,
            'claim':policy['claim']+' Selected report: '+kind+'.','scope_ref':policy['scope_ref'],
            'required_fields':wanted,'required_outcome':policy['required_outcome'][kind]}
