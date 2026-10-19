"""Read-only capture-plan validation and a qualified wrapper command renderer."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
import re

PROFILE='verilator-5.020-vcd-wrapper.v1'
FS={'s':10**15,'ms':10**12,'us':10**9,'ns':10**6,'ps':10**3,'fs':1}
NAME=re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*\Z')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def shape(value,keys,optional=()):
    require(isinstance(value,dict) and set(keys)<=set(value) and set(value)<=set(keys)|set(optional),
            'Invalid fields; expected '+', '.join(keys))


def text(value):
    return isinstance(value,str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'Duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+v)))


class TimeGap(ValueError):
    pass


class TimeMismatch(ValueError):
    pass


def quantity(value):
    shape(value,('value','unit'))
    require(value['unit'] is None or value['unit'] in {*FS,'cycles'},'Unsupported time unit')
    require(value['value'] is None or isinstance(value['value'],str),'Use decimal strings for time values')
    if value['value'] is not None:
        try:
            number=Decimal(value['value'])
        except InvalidOperation as error:
            raise ValueError('Invalid decimal time value') from error
        require(number.is_finite(),'Time values must be finite')


def physical_fs(value):
    quantity(value)
    if value['value'] is None or value['unit'] is None:
        raise TimeGap('Unknown simulation-time quantity')
    require(value['unit'] in FS,'Physical time quantity required')
    return Fraction(Decimal(value['value']))*FS[value['unit']]


def ticks(value,tick,clock):
    quantity(value)
    if value['value'] is None or value['unit'] is None:
        raise TimeGap('Unknown simulation time')
    if value['unit']=='cycles':
        if clock is None or clock['kind']!='affine_edge_index' or not text(clock['clock_ref']) or not text(clock['evidence_ref']):
            raise TimeGap('Cycle conversion requires an evidenced affine clock edge relation')
        period=physical_fs(clock['period'])
        if period<=0:
            raise TimeMismatch('Clock period must be positive')
        total=physical_fs(clock['origin'])+Fraction(Decimal(value['value']))*period
    else:
        total=physical_fs(value)
    resolution=physical_fs(tick)
    if resolution<=0:
        raise TimeMismatch('Native tick resolution must be positive')
    result=total/resolution
    if result<0 or result.denominator!=1:
        raise TimeMismatch('Requested time is negative or not exactly representable in native ticks')
    return result.numerator


def validate_inventory(value):
    shape(value,('format','profile','namespace','binary_sha256','tick','max_tick','trace_compiled','complete','objects','aliases','source'))
    canonical(value)
    require(value['format']=='opentools.trace-inventory.v1' and text(value['profile']) and value['namespace']=='vcd_declarations','Invalid trace inventory')
    require(value['binary_sha256'] is None or digest(value['binary_sha256']),'Invalid binary digest')
    quantity(value['tick'])
    require(value['tick']['unit']!='cycles','Native tick needs a physical time unit')
    require(value['max_tick'] is None or type(value['max_tick']) is int and 0<value['max_tick']<=2**64-1,'Invalid native tick bound')
    require(all(value[k] is None or type(value[k]) is bool for k in ('trace_compiled','complete')),'Invalid inventory completeness/capability')
    shape(value['source'],('header_sha256','context_sha256','evidence_ref'))
    require(all(value['source'][k] is None or digest(value['source'][k]) for k in ('header_sha256','context_sha256'))
            and nullable(value['source']['evidence_ref']),'Invalid source binding')
    require(isinstance(value['objects'],list) and isinstance(value['aliases'],list),'Invalid object/alias lists')
    names=set();widths={}
    for item in value['objects']:
        shape(item,('path','id_code','width','kind','selectable','selector','viewer_name'))
        require(text(item['path']) and item['path'] not in names and nullable(item['id_code']) and nullable(item['kind'])
                and (item['width'] is None or type(item['width']) is int and item['width']>0)
                and (item['selectable'] is None or type(item['selectable']) is bool)
                and nullable(item['selector']) and nullable(item['viewer_name']),'Invalid trace object')
        names.add(item['path'])
        if item['id_code'] is not None and item['width'] is not None:
            require(item['id_code'] not in widths or widths[item['id_code']]==item['width'],'Trace aliases disagree about width')
            widths[item['id_code']]=item['width']
    aliases=set()
    for item in value['aliases']:
        shape(item,('name','target','evidence_ref'))
        require(text(item['name']) and item['name'] not in names|aliases and item['target'] in names
                and nullable(item['evidence_ref']),'Invalid/ambiguous semantic alias')
        aliases.add(item['name'])


def validate_plan(value):
    shape(value,('format','plan_ref','question','original_run_ref','inventory_sha256','operation','waveform_format','window','failure',
                 'clock','objects','history','correspondence','intent','run','expansion'),('provenance',))
    canonical(value)
    require(value['format']=='opentools.capture-plan.v1' and text(value['plan_ref']),'Invalid capture plan')
    require(nullable(value['question']) and nullable(value['original_run_ref']) and (value['inventory_sha256'] is None or digest(value['inventory_sha256'])),
            'Invalid question/source/inventory binding')
    require(value['operation'] in ('capture_time','postprocess') and text(value['waveform_format'])
            and value['intent'] in ('reproduce','exploratory'),'Invalid operation/format/intent')
    shape(value['window'],('start','end','evidence_ref'))
    quantity(value['window']['start']); quantity(value['window']['end'])
    require(nullable(value['window']['evidence_ref']),'Invalid window basis')
    shape(value['failure'],('time','evidence_ref'))
    quantity(value['failure']['time'])
    require(nullable(value['failure']['evidence_ref']),'Invalid failure observation')
    if value['clock'] is not None:
        shape(value['clock'],('kind','clock_ref','period','origin','evidence_ref'))
        require(value['clock']['kind'] in ('affine_edge_index','unknown') and nullable(value['clock']['clock_ref'])
                and nullable(value['clock']['evidence_ref']),'Invalid clock relation')
        quantity(value['clock']['period']);quantity(value['clock']['origin'])
        require(value['clock']['period']['unit']!='cycles' and value['clock']['origin']['unit']!='cycles','Clock relation needs physical units')
    require(isinstance(value['objects'],list) and isinstance(value['expansion'],list),'Objects/expansion must be lists')
    names=set()
    for item in value['objects']:
        shape(item,('name','role','rationale','evidence_ref'))
        require(text(item['name']) and item['name'] not in names and all(nullable(item[k]) for k in ('role','rationale','evidence_ref')),
                'Invalid/duplicate selection')
        names.add(item['name'])
    for item in value['expansion']:
        shape(item,('trigger','action','evidence_ref'))
        require(all(nullable(item[k]) for k in item),'Invalid expansion condition')
    shape(value['history'],('method','available_from','evidence_ref'))
    require(value['history']['method'] in ('new_run','replay_from_reset','existing_trace','error_trigger','rolling_buffer')
            and nullable(value['history']['evidence_ref']),'Invalid history method')
    if value['history']['available_from'] is not None:
        quantity(value['history']['available_from'])
    shape(value['correspondence'],('status','evidence_ref'))
    require(value['correspondence']['status'] in ('matched_selected_observables','unknown','diverged','not_applicable')
            and nullable(value['correspondence']['evidence_ref']),'Invalid replay correspondence')
    shape(value['run'],('stop','argv','evidence_ref'))
    quantity(value['run']['stop'])
    require(isinstance(value['run']['argv'],list) and all(isinstance(v,str) for v in value['run']['argv'])
            and nullable(value['run']['evidence_ref']),'Run argv must preserve literal argument strings')


def assess(plan,inventory,binary=None):
    validate_inventory(inventory);validate_plan(plan)
    rejected=[];gaps=[];warnings=[]
    if inventory['profile']!=PROFILE:
        rejected.append('Unsupported native wrapper profile')
    if inventory['trace_compiled'] is False:
        rejected.append('Binary is declared without trace instrumentation')
    if inventory['trace_compiled'] is not True or inventory['complete'] is not True:
        gaps.append('Trace capability/namespace completeness is not established')
    if plan['inventory_sha256']!=fingerprint(inventory):
        gaps.append('Plan does not bind this exact trace inventory')
    if any(inventory['source'][k] is None for k in ('header_sha256','context_sha256')) or not text(inventory['source']['evidence_ref']):
        gaps.append('Missing original header/producer context evidence')
    if plan['operation']!='capture_time':
        rejected.append('Post-processing cannot be rendered as reduced native capture work')
    if plan['waveform_format']!='vcd':
        rejected.append('This wrapper profile supports VCD only')
    for name,value in [('question',plan['question']),('original run',plan['original_run_ref']),('window',plan['window']['evidence_ref']),
                       ('failure',plan['failure']['evidence_ref']),('run settings',plan['run']['evidence_ref'])]:
        if not text(value):
            gaps.append('Missing '+name+' basis')
    converted={}
    for name,value in [('start',plan['window']['start']),('end',plan['window']['end']),('failure',plan['failure']['time']),('stop',plan['run']['stop'])]:
        try:
            converted[name]=ticks(value,inventory['tick'],plan['clock'])
        except TimeGap as error:
            gaps.append(name+': '+str(error))
        except TimeMismatch as error:
            rejected.append(name+': '+str(error))
    if {'start','end'}<=converted.keys() and converted['end']<=converted['start']:
        rejected.append('Capture window must have a positive extent')
    if {'end','stop'}<=converted.keys() and converted['stop']<converted['end']:
        rejected.append('Simulation stops before the requested capture ends')
    if inventory['max_tick'] is None:
        gaps.append('Native wrapper tick bounds are not established')
    elif any(converted[name]>inventory['max_tick'] for name in ('start','end','stop') if name in converted):
        rejected.append('Requested controls exceed the declared native wrapper tick bound; nothing is truncated')
    if {'start','end','failure'}<=converted.keys() and not converted['start']<=converted['failure']<=converted['end']:
        warnings.append('Failure observation lies outside the selected window')
    history=plan['history']
    if history['method'] not in ('new_run','replay_from_reset'):
        rejected.append('This renderer supports scheduled new/reset runs; no trigger, rolling buffer or existing-file filtering API is inferred')
    if history['available_from'] is None or not text(history['evidence_ref']):
        gaps.append('Earliest available history is not established')
    else:
        try:
            first=ticks(history['available_from'],inventory['tick'],plan['clock'])
            if 'start' in converted and first>converted['start']:
                rejected.append('Requested pre-failure history predates available capture/replay data')
        except TimeGap as error:
            gaps.append('history: '+str(error))
        except TimeMismatch as error:
            rejected.append('history: '+str(error))
    objects={item['path']:item for item in inventory['objects']}
    aliases={item['name']:item for item in inventory['aliases']}
    resolved=[]
    if not plan['objects']:
        gaps.append('No observation objects selected')
    for requested in plan['objects']:
        name=requested['name']
        alias=aliases.get(name)
        target=alias['target'] if alias else name
        if alias and not text(alias['evidence_ref']):
            gaps.append('Unsourced semantic alias: '+name)
        if target not in objects:
            rejected.append('Not found in the supplied trace declaration namespace: '+target)
            continue
        item=objects[target]
        if item['selectable'] is False or not NAME.fullmatch(target) or item['selector'] is not None and item['selector']!=target:
            rejected.append('Unsupported native leaf selector (arrays/escaped names need another qualified mapping): '+target)
        if item['selectable'] is None or any(item[k] is None for k in ('selector','id_code','width','viewer_name')):
            gaps.append('Object visibility/selection basis unknown: '+target)
        if item['viewer_name'] is not None and item['viewer_name']!=target and not re.fullmatch(re.escape(target)+r'\[-?\d+:-?\d+\]',item['viewer_name']):
            rejected.append('Unsupported viewer-name mapping: '+target)
        if any(not text(requested[k]) for k in ('role','rationale','evidence_ref')):
            gaps.append('Missing signal role/rationale/source: '+name)
        resolved.append({'requested':name,'path':target,'selector':item['selector'],'viewer_name':item['viewer_name'],
                         'width':item['width'],'id_code':item['id_code'],
                         'trace_aliases':[v['path'] for v in inventory['objects'] if v['id_code'] is not None and v['id_code']==item['id_code']]})
    selected=list(dict.fromkeys(v['path'] for v in resolved))
    # dumpvars(1, leaf) can also include one level below an identically named
    # aggregate. Report this declaration expansion; never silently call it exact.
    emitted=[v['path'] for v in inventory['objects'] if any(v['path']==name or v['path'].startswith(name+'.')
             and v['path'][len(name)+1:].count('.')==0 for name in selected)]
    extra=[name for name in emitted if name not in selected]
    if extra:
        warnings.append('Native prefix/depth semantics include additional declarations; inspect native_extra_objects')
    correspondence=plan['correspondence']
    label='exploratory_branch' if plan['intent']=='exploratory' else 'new_planned_run' if history['method']=='new_run' else 'unqualified_replay'
    if correspondence['status']=='diverged' and plan['intent']=='reproduce':
        rejected.append('Known replay divergence cannot be presented as reproduction')
    if correspondence['status']=='matched_selected_observables' and text(correspondence['evidence_ref']) and plan['intent']=='reproduce':
        label='previously_compared_within_supplied_scope'
    if label=='unqualified_replay':
        warnings.append('Original/replay correspondence is unestablished; capture attempt is not a reproduction proof')
    if not plan['expansion'] or any(not text(v['trigger']) or not text(v['action']) or not text(v['evidence_ref']) for v in plan['expansion']):
        gaps.append('A sourced scope/window expansion strategy is required')
    binary_info={'path':str(Path(binary).resolve()) if binary else None,'expected_sha256':inventory['binary_sha256'],'observed_sha256':None}
    if inventory['binary_sha256'] is None or binary is None:
        gaps.append('Explicit current binary and original binary digest are required')
    elif not Path(binary).is_file():
        rejected.append('Current binary is unavailable')
    else:
        binary_info['observed_sha256']=hashlib.sha256(Path(binary).read_bytes()).hexdigest()
        if binary_info['observed_sha256']!=inventory['binary_sha256']:
            rejected.append('Current binary differs from the trace inventory producer')
    warnings.append('Signal/window adequacy and causality require engineering review; a local cone is a starting hypothesis')
    return {'format':'opentools.capture-assessment.v1','status':'rejected' if rejected else 'incomplete' if gaps else 'renderable',
            'input_sha256':{'plan':fingerprint(plan),'inventory':fingerprint(inventory)},'binary':binary_info,
            'native_ticks':converted,'resolved':resolved,'expected_declarations':emitted,'native_extra_objects':extra,
            'replay_label':label,'rejections':list(dict.fromkeys(rejected)),'unknowns':list(dict.fromkeys(gaps)),
            'warnings':warnings,'limits':'Command readiness within supplied evidence/profile, not native execution, trace adequacy, causality or reproduction qualification.'}


def render(plan,inventory,binary,wave_path):
    report=assess(plan,inventory,binary)
    require(report['status']=='renderable','Capture plan is not renderable; inspect its assessment')
    output=Path(wave_path).resolve()
    require(not output.exists() and output.parent.is_dir(),'Choose a new waveform path with an existing parent')
    command=[str(Path(binary).resolve()),'--capture-vcd',str(output),'--start-tick',str(report['native_ticks']['start']),
             '--end-tick',str(report['native_ticks']['end']),'--stop-tick',str(report['native_ticks']['stop'])]
    for name in dict.fromkeys(v['selector'] for v in report['resolved']):
        command+=['--select',name]
    command+=['--',*plan['run']['argv']]
    return {'format':'opentools.capture-recipe.v1','profile':PROFILE,'assessment':report,'argv':command,
            'shell':False,'waveform_path':str(output),'window_semantics':'inclusive first/last dump ticks after eval; simulation still runs from reset',
            'viewer':{'format':'GTKWave selection instructions','dumpfile':str(output),
                      'signals':list(dict.fromkeys(v['viewer_name'] for v in report['resolved'])),
                      'start_tick':report['native_ticks']['start'],'failure_tick':report['native_ticks'].get('failure')},
            'limits':'Preview only; execute through the existing authorized runner after inspection. No callback, shell, checkpoint restore, model-provider or DVIT installation is performed.'}


def exit_code(report):
    return {'renderable':0,'rejected':1,'incomplete':2}[report['status']]
