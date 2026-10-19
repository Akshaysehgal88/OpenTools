import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from capture_core import PROFILE,assess,render,ticks,fingerprint,read_json,validate_inventory
spec=importlib.util.spec_from_file_location('capture_example',ROOT/'examples/create_example.py')
example_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(example_module)
HAS_VCD=importlib.util.find_spec('vcd') is not None


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.p,self.i,binary=example_module.example()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.binary=self.root/'sim.bin';self.binary.write_bytes(binary)

    def assess(self):
        return assess(self.p,self.i,self.binary)

    def bind(self):
        self.p['inventory_sha256']=fingerprint(self.i)

    def test_cycle_relation_exact_tick_conversion(self):
        report=self.assess()
        self.assertEqual(report['status'],'renderable')
        self.assertEqual(report['native_ticks'],{'start':110,'end':250,'failure':240,'stop':260})
        self.assertEqual(report['replay_label'],'unqualified_replay')

    def test_physical_units_and_decimal_values(self):
        self.p['window']['start']={'value':'0.11','unit':'us'}
        self.p['window']['end']={'value':'250000','unit':'ps'}
        self.assertEqual(self.assess()['native_ticks']['start'],110)
        self.assertEqual(self.assess()['native_ticks']['end'],250)

    def test_non_integral_tick_is_rejected_without_rounding(self):
        self.p['window']['start']={'value':'110.5','unit':'ns'}
        self.assertEqual(self.assess()['status'],'rejected')

    def test_cycle_conversion_needs_actual_clock_relation(self):
        self.p['clock']=None
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_variable_unknown_clock_is_not_constant_period(self):
        self.p['clock']['kind']='unknown'
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_origin_offset_preserved(self):
        self.p['clock']['origin']={'value':'3','unit':'ns'}
        self.assertEqual(self.assess()['native_ticks']['start'],113)

    def test_large_time_counter_does_not_lose_low_bits(self):
        value=2**128+1
        result=ticks({'value':str(value),'unit':'cycles'},self.i['tick'],self.p['clock'])
        self.assertEqual(result,2*value)

    def test_binary_profile_bounds_reject_not_clip(self):
        self.p['run']['stop']={'value':'1000001','unit':'ns'}
        self.assertEqual(self.assess()['status'],'rejected')
        self.i['max_tick']=None;self.bind()
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_window_order_and_run_extent(self):
        self.p['window']['end']={'value':'10','unit':'ns'}
        self.assertEqual(self.assess()['status'],'rejected')
        self.p['window']['end']={'value':'300','unit':'ns'}
        self.assertEqual(self.assess()['status'],'rejected')

    def test_failure_outside_window_is_visible_warning_not_causality_verdict(self):
        self.p['window']['end']={'value':'119','unit':'cycles'}
        report=self.assess()
        self.assertEqual(report['status'],'renderable')
        self.assertIn('Failure observation lies outside the selected window',report['warnings'])

    def test_semantic_alias_resolves_actual_object_and_trace_aliases(self):
        report=self.assess()
        value=next(v for v in report['resolved'] if v['requested']=='accepted_transaction')
        self.assertEqual(value['path'],'TOP.top.dma.accepted')
        self.assertIn('TOP.top.accepted',value['trace_aliases'])

    def test_unseen_object_is_not_invented(self):
        self.p['objects'][0]['name']='TOP.top.unknown'
        self.assertEqual(self.assess()['status'],'rejected')

    def test_missing_alias_evidence_stays_unknown(self):
        self.i['aliases'][0]['evidence_ref']=None;self.bind()
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_array_element_cannot_be_mistaken_for_native_leaf(self):
        self.i['objects'].append({'path':'TOP.top.memory[0]','id_code':'X','width':8,'kind':'wire',
                   'selectable':False,'selector':None,'viewer_name':'TOP.top.memory[0][7:0]'})
        self.p['objects'][0]['name']='TOP.top.memory[0]';self.bind()
        self.assertEqual(self.assess()['status'],'rejected')

    def test_unknown_selector_is_unknown_not_known_absent(self):
        self.i['objects'][0].update(selectable=None,selector=None);self.bind()
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_prefix_depth_collateral_is_reported(self):
        self.i['objects'].append({'path':'TOP.top.dma.outstanding.field','id_code':'X','width':1,'kind':'wire',
              'selectable':True,'selector':'TOP.top.dma.outstanding.field','viewer_name':'TOP.top.dma.outstanding.field'})
        self.bind()
        report=self.assess()
        self.assertEqual(report['native_extra_objects'],['TOP.top.dma.outstanding.field'])
        self.assertTrue(any('additional declarations' in v for v in report['warnings']))

    def test_corrupt_or_foreign_binary_is_rejected(self):
        self.binary.write_bytes(b'other binary')
        self.assertEqual(self.assess()['status'],'rejected')

    def test_instrumentation_and_header_source_are_required(self):
        self.i['trace_compiled']=False;self.bind()
        self.assertEqual(self.assess()['status'],'rejected')
        self.i['trace_compiled']=True;self.i['source']['header_sha256']=None;self.bind()
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_foreign_inventory_binding_is_incomplete(self):
        self.i['source']['evidence_ref']='new namespace source'
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_unqualified_native_format_or_profile_is_rejected(self):
        self.p['waveform_format']='fsdb'
        self.assertEqual(self.assess()['status'],'rejected')
        self.p['waveform_format']='vcd';self.i['profile']='other-wrapper';self.bind()
        self.assertEqual(self.assess()['status'],'rejected')

    def test_postprocessing_does_not_claim_capture_savings(self):
        self.p['operation']='postprocess'
        self.assertEqual(self.assess()['status'],'rejected')

    def test_error_trigger_cannot_recover_unrecorded_past(self):
        self.p['history'].update(method='error_trigger',available_from={'value':'240','unit':'ns'})
        report=self.assess()
        self.assertEqual(report['status'],'rejected')
        self.assertTrue(any('predates available' in v for v in report['rejections']))

    def test_unestablished_history_or_expansion_blocks_render(self):
        self.p['history']['available_from']=None
        self.assertEqual(self.assess()['status'],'incomplete')
        self.p['history']['available_from']={'value':'0','unit':'ns'};self.p['expansion']=[]
        self.assertEqual(self.assess()['status'],'incomplete')

    def test_diverged_replay_needs_exploratory_intent(self):
        self.p['correspondence'].update(status='diverged',evidence_ref='actual mismatch')
        self.assertEqual(self.assess()['status'],'rejected')
        self.p['intent']='exploratory'
        self.assertEqual(self.assess()['status'],'renderable')
        self.assertEqual(self.assess()['replay_label'],'exploratory_branch')

    def test_known_correspondence_remains_scoped(self):
        self.p['correspondence'].update(status='matched_selected_observables',evidence_ref='saved exact comparison')
        self.assertEqual(self.assess()['replay_label'],'previously_compared_within_supplied_scope')

    def test_renderer_uses_literal_argv_and_native_depth_is_fixed(self):
        self.p['run']['argv']=['literal; not a shell command','$(still-literal)']
        recipe=render(self.p,self.i,self.binary,self.root/'capture with space.vcd')
        self.assertFalse(recipe['shell'])
        self.assertEqual(recipe['argv'][-2:],self.p['run']['argv'])
        self.assertIn('--select',recipe['argv'])
        self.assertFalse((self.root/'capture with space.vcd').exists())

    def test_existing_wavefile_is_not_overwritten(self):
        (self.root/'wave.vcd').write_bytes(b'existing')
        with self.assertRaises(ValueError):
            render(self.p,self.i,self.binary,self.root/'wave.vcd')

    def test_ambiguous_semantic_alias_and_conflicting_alias_widths_rejected(self):
        bad=copy.deepcopy(self.i)
        bad['aliases'][0]['name']=bad['objects'][0]['path']
        with self.assertRaises(ValueError):
            validate_inventory(bad)
        self.i['objects'][-1]['width']=2
        with self.assertRaises(ValueError):
            validate_inventory(self.i)

    def test_nonfinite_time_and_duplicate_json_keys_rejected(self):
        self.p['window']['start']['value']='NaN'
        with self.assertRaises(ValueError):
            self.assess()
        path=self.root/'duplicate.json';path.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            read_json(path)

    def test_cli_status_and_output_preservation(self):
        for name,value in [('plan',self.p),('inventory',self.i)]:
            (self.root/(name+'.json')).write_text(json.dumps(value))
        argv=[sys.executable,str(ROOT/'waveform_capture.py'),'assess',str(self.root/'plan.json'),str(self.root/'inventory.json'),'--binary',str(self.binary)]
        self.assertEqual(subprocess.run(argv,capture_output=True).returncode,0)
        self.assertEqual(subprocess.run(argv+['--output',str(self.binary)],capture_output=True).returncode,3)
        self.p['inventory_sha256']=None
        (self.root/'plan.json').write_text(json.dumps(self.p))
        self.assertEqual(subprocess.run(argv,capture_output=True).returncode,2)
        self.p['waveform_format']='fst'
        (self.root/'plan.json').write_text(json.dumps(self.p))
        self.assertEqual(subprocess.run(argv,capture_output=True).returncode,1)


@unittest.skipUnless(HAS_VCD,'optional pyvcd==0.5.0 is not installed')
class VCDTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'native.vcd'
        self.header=b'$version Generated by VerilatedVcd $end\n$timescale 1ns $end\n$scope module TOP $end\n$var wire 1 ! clk $end\n$var wire 8 " data [7:0] $end\n$var wire 8 " data_alias [7:0] $end\n$var wire 4 # mem[0] [3:0] $end\n$upscope $end\n$enddefinitions $end\n'
        self.path.write_bytes(self.header+b'#0\n0!\nb0 "\n')

    def test_native_header_aliases_ranges_and_array_limit(self):
        from native_vcd import inspect_header
        info=inspect_header(self.path)
        self.assertEqual(info['header_sha256'],hashlib.sha256(self.header).hexdigest())
        self.assertEqual(info['objects'][1]['viewer_name'],'TOP.data[7:0]')
        self.assertEqual(info['objects'][1]['id_code'],info['objects'][2]['id_code'])
        self.assertFalse(info['objects'][3]['selectable'])

    def test_input_identity_is_header_prefix_not_waveform_body(self):
        from native_vcd import inspect_header
        first=inspect_header(self.path)
        self.path.write_bytes(self.header+b'#99\n1!\nb111 "\n')
        self.assertEqual(first,inspect_header(self.path))

    def test_producer_context_must_bind_header_and_version(self):
        from native_vcd import inspect_header,context_template,import_inventory
        info=inspect_header(self.path);context=context_template(info)
        context.update(producer_version='5.020 2024-01-01',binary_sha256='a'*64,max_tick=1000000,trace_compiled=True,evidence_ref='captured producer')
        inventory=import_inventory(self.path,context)
        self.assertEqual(inventory['max_tick'],1000000)
        context['header_sha256']='b'*64
        with self.assertRaises(ValueError):
            import_inventory(self.path,context)
        context['header_sha256']=info['header_sha256'];context['producer_version']='5.052'
        with self.assertRaises(ValueError):
            import_inventory(self.path,context)

    def test_truncated_unbalanced_or_foreign_header_rejected(self):
        from native_vcd import inspect_header
        for content in (self.header.split(b'$enddefinitions')[0],self.header.replace(b'$upscope $end\n',b''),self.header.replace(b'Generated by VerilatedVcd',b'other writer')):
            self.path.write_bytes(content)
            with self.assertRaises(ValueError):
                inspect_header(self.path)


class NativeTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('OPENTOOLS_WAVEFORM_NATIVE'),'set OPENTOOLS_WAVEFORM_NATIVE to Verilator 5.020 executable')
    def test_actual_window_selectors_expansion_and_reproduction(self):
        with tempfile.TemporaryDirectory(prefix='opentools-waveform-test-') as folder:
            out=Path(folder)/'case'
            result=subprocess.run([sys.executable,str(ROOT/'examples/verilator/run_example.py'),
                '--verilator',os.environ['OPENTOOLS_WAVEFORM_NATIVE'],'--verilator-root',os.environ['VERILATOR_ROOT'],
                '--directory',str(out),'--timing-repeats','1'],capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stderr)
            data=read_json(out/'summary.json')
            self.assertTrue(data['causal_observations']['initial_insufficient'])
            self.assertEqual(data['captures']['initial']['declarations'],7)
            self.assertEqual(data['captures']['expanded']['declarations'],13)
            self.assertLess(data['captures']['expanded']['bytes'],data['captures']['full']['bytes'])
            self.assertEqual(data['captures']['expanded']['first_tick'],110)
            original=read_json(out/'original-uninstrumented.invocation.json')
            for name in ('full','initial','request-window','expanded'):
                self.assertEqual(read_json(out/(name+'.invocation.json'))['stdout'],original['stdout'])
            rows=[json.loads(line) for line in original['stdout'].splitlines()]
            self.assertEqual(next(v['tick'] for v in rows if v['quiesce']),120)
            self.assertEqual(next(v['tick'] for v in rows if v['accepted']),180)
            self.assertEqual(next(v['tick'] for v in rows if v['timeout']),240)
            self.assertTrue((out/'expanded.gtkw').read_text().startswith('[dumpfile]'))
            binary=out/'traced.bin'
            bad=subprocess.run([str(binary),'--invented-control','x'],capture_output=True)
            self.assertEqual(bad.returncode,3)
            no_trace=subprocess.run([str(out/'plain.bin'),'--inventory-vcd',str(out/'unavailable.vcd')],capture_output=True)
            self.assertEqual(no_trace.returncode,3)
            self.assertFalse((out/'unavailable.vcd').exists())


if __name__=='__main__':
    unittest.main()
