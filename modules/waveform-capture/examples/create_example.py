"""Create synthetic plan/inventory inputs for a preview without native tools."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from capture_core import PROFILE,fingerprint


def example():
    binary=b'synthetic wrapper identity; not an executable\n'
    paths=['TOP.top.clk','TOP.top.reset_n','TOP.top.dma.accepted','TOP.top.dma.outstanding','TOP.top.dma.timeout','TOP.top.accepted']
    objects=[{'path':path,'id_code':str(i if i<5 else 2),'width':1,'kind':'wire','selectable':True,'selector':path,'viewer_name':path}
             for i,path in enumerate(paths)]
    inventory={'format':'opentools.trace-inventory.v1','profile':PROFILE,'namespace':'vcd_declarations',
               'binary_sha256':hashlib.sha256(binary).hexdigest(),'tick':{'value':'1','unit':'ns'},'trace_compiled':True,
               'max_tick':1000000,'complete':True,'objects':objects,
               'aliases':[{'name':'accepted_transaction','target':'TOP.top.dma.accepted','evidence_ref':'synthetic:local interface map'}],
               'source':{'header_sha256':'a'*64,'context_sha256':'b'*64,'evidence_ref':'synthetic:declarations and producer context'}}
    plan={'format':'opentools.capture-plan.v1','plan_ref':'synthetic:request-window','question':'Was the request accepted before the timeout?',
          'original_run_ref':'synthetic:original','inventory_sha256':fingerprint(inventory),'operation':'capture_time','waveform_format':'vcd',
          'window':{'start':{'value':'55','unit':'cycles'},'end':{'value':'125','unit':'cycles'},'evidence_ref':'synthetic:transaction marker'},
          'failure':{'time':{'value':'120','unit':'cycles'},'evidence_ref':'synthetic:timeout marker'},
          'clock':{'kind':'affine_edge_index','clock_ref':'TOP.top.clk','period':{'value':'2','unit':'ns'},
                   'origin':{'value':'0','unit':'ns'},'evidence_ref':'synthetic:known constant rising-edge relation'},
          'objects':[{'name':name,'role':'clock/reset' if name.endswith(('clk','reset_n')) else 'transaction state',
                      'rationale':'Observe acceptance, progress and timing context','evidence_ref':'synthetic:connectivity'}
                     for name in ['TOP.top.clk','TOP.top.reset_n','accepted_transaction','TOP.top.dma.outstanding','TOP.top.dma.timeout']],
          'history':{'method':'replay_from_reset','available_from':{'value':'0','unit':'ns'},'evidence_ref':'synthetic:scheduled from reset'},
          'correspondence':{'status':'unknown','evidence_ref':None},'intent':'reproduce',
          'run':{'stop':{'value':'260','unit':'ns'},'argv':['--request-cycle','90','--config-cycle','60','--config-value','1'],
                 'evidence_ref':'synthetic:original arguments'},
          'expansion':[{'trigger':'State predates the first dump or upstream grant remains unexplained',
                        'action':'Expand earlier and add source-side arbitration/control signals','evidence_ref':'synthetic:causal hypothesis'}]}
    return plan,inventory,binary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory');args=parser.parse_args()
    out=Path(args.directory);out.mkdir(exist_ok=False)
    plan,inventory,binary=example()
    for name,value in [('plan',plan),('inventory',inventory)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'sim.bin').write_bytes(binary)


if __name__=='__main__':
    main()
