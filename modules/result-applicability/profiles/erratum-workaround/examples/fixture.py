"""One independent synthetic notice and two owned maintenance contexts."""
from pathlib import Path
from erratum_common import IDENTITY,MODEL,digest
HERE=Path(__file__).resolve().parent
FAMILIES={'ordering-boundary':2,'reset-boundary':3}
CASES=('affected-unmitigated','affected-mitigated','fixed-base-vulnerable','unaffected','feature-disabled','unknown-fuse','interaction-conflict','too-short-guard','ported-guard','feature-disabled-unknown-fuse','fuse-repaired','normal-mode')
def config(family,case):
    return {'revision':2 if case in ('fixed-base-vulnerable','unaffected') else 1,'actual_fuse':int(case=='fuse-repaired'),'fuse_readable':int(case not in ('unknown-fuse','feature-disabled-unknown-fuse')),'feature':int(case not in ('feature-disabled','feature-disabled-unknown-fuse')),'fast_mode':int(case!='normal-mode'),'guard_need':FAMILIES[family],'exception_enabled':int(case=='interaction-conflict'),'power_on':1}
def config_text(family,case):return ''.join(k+' '+str(v)+'\n' for k,v in sorted(config(family,case).items()))
def program(family,case):
    need=FAMILIES[family];wa=case in ('affected-mitigated','unknown-fuse','interaction-conflict','too-short-guard','ported-guard')
    rows=[('WRITE',42)]
    if case in ('unaffected','unknown-fuse','fuse-repaired'):rows.append(('BASE_FENCE',0))
    if wa:rows += [('WA_FENCE',0),('WA_GUARD',need-1 if case=='too-short-guard' else 2 if case=='ported-guard' else need)]
    return rows+[('ISSUE',0)]
def program_text(family,case):return '# owned event-delivery command image\n'+''.join(op+' '+str(arg)+'\n' for op,arg in program(family,case))
def context(family,case):
    return {'format':'opentools.erratum-context.v1','run_ref':family+'-'+case,'scope_ref':family+'/maintenance','configuration_ref':family+'/'+case,'mode_ref':'normal' if case=='normal-mode' else 'fast','model_ref':MODEL}
def notice():
    basis='owned/OWNED-E001/revision1';fact=lambda v:{'value':v,'evidence_ref':basis}
    leaf=lambda field,value:{'op':'equal','field':field,'value':value,'basis_ref':basis}
    return {'format':'opentools.erratum-notice.v1','notice_id':'OWNED-E001','revision':'1','source_ref':basis,'owner_ref':basis+'#notice-owner',
      'predicate':{'op':'all','basis_ref':basis,'terms':[leaf('path.feature_enabled',True),leaf('clock.fast_mode',True),leaf('power.on',True),{'op':'any','basis_ref':basis,'terms':[{'op':'all','basis_ref':basis,'terms':[{'op':'in','field':'silicon.revision','value':[1],'basis_ref':basis},leaf('silicon.repair_fuse',False)]},leaf('firmware.base_ordered',False)]}]},
      'profiles':{family:{'scope_ref':family+'/maintenance','min_guard_ticks':need,'basis_ref':basis+'#'+family} for family,need in FAMILIES.items()},
      'mitigation':{'guard_field':'workaround.guard_ticks','required_fields':{'firmware.wa_ordered':fact(True),'workaround.force_clock':fact(True)},'source_ref':basis+'#guard-and-ordering'},
      'interaction':{'id':'owned-idle-clock-exception','enabled_field':'power.exception_enabled','required_fields':{'workaround.force_clock':{'value':False,'evidence_ref':'owned/idle-clock-exception/premise'}} ,'source_ref':'owned/idle-clock-exception/premise','owner_ref':'owned/idle-clock-exception/owner'}}
def request(family,case,c,sources,command_sha,context_sha):
    basis='owned/'+family+'/independent-maintenance-question';fact=lambda v:{'value':v,'evidence_ref':basis};n=notice()
    intent='apply' if case in ('affected-unmitigated','fixed-base-vulnerable') else 'remove' if case in ('unaffected','feature-disabled','feature-disabled-unknown-fuse','fuse-repaired','normal-mode') else 'retain'
    cut='owned-review-cut-r1';approval={'status':'approved','source_ref':basis+'#supplied-decision','decision_ref':basis+'#owned-fixture-only','cut_ref':cut,'notice_sha256':digest(n),'scope_ref':c['scope_ref'],'mode_ref':c['mode_ref'],'image_sha256':sources['firmware.txt'],'intent':intent}
    values={'scope.identity':{k:c[k] for k in IDENTITY[1:]},'source.kind':MODEL,'source.model_sha256':sources['device.cpp'],'firmware.image_sha256':sources['firmware.txt'],'native.guard_need':FAMILIES[family]}
    return {'format':'opentools.erratum-request.v1','claim_ref':family+'/'+case+'/maintenance','scope_ref':c['scope_ref'],'run_ref':c['run_ref'],'owner_ref':basis+'#maintenance-owner','requirements_ref':basis,'review_cut_ref':cut,'intent':intent,'notice_profile':family,'notice_sha256':digest(n),'binding':{'identity':{k:c[k] for k in IDENTITY},'sources':sources,'context_sha256':context_sha,'command_sha256':command_sha},'required_fields':{k:fact(v) for k,v in values.items()},'approval':approval}
