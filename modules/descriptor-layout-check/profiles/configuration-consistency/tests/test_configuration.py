import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1];MODULE=PROFILE.parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples'),str(MODULE)]
from configuration_core import digest,exit_code,read_json,review
from create_example import example,save
from layout_capture import hardware,software,source_ref

def bind(values):
    for name,capture in zip(('hardware','software'),values[:2]):values[2]['views'][name]['export_sha256']=digest(capture)
def kinds(report,field='findings'):return {v['kind'] for v in report[field]}
def width(report):return report['parameters'][0]['observations']

class ConfigurationTests(unittest.TestCase):
    def test_64_bits_and_8_bytes_agree_only_through_explicit_conversion(self):
        result=review(*example('payload-matched'));self.assertEqual(exit_code(result),0)
        self.assertEqual(width(result)['hardware']['raw_value'],64);self.assertEqual(width(result)['software']['raw_value'],8)
        self.assertEqual(width(result)['software']['canonical_value'],64)

    def test_equal_raw_numbers_with_different_units_are_a_real_mismatch(self):
        result=review(*example('payload-same-number'));self.assertEqual(width(result)['hardware']['raw_value'],width(result)['software']['raw_value'])
        self.assertEqual(width(result)['software']['canonical_value'],512);self.assertEqual(exit_code(result),1)

    def test_stale_default_comes_from_actual_effective_value(self):
        result=review(*example('payload-stale-default'));self.assertEqual(width(result)['software']['raw_value'],4)
        self.assertEqual(width(result)['software']['canonical_value'],32);self.assertIn('required_parameter_mismatch',kinds(result))

    def test_two_sources_can_agree_on_wrong_default(self):
        result=review(*example('storage-agree-wrong-default'));self.assertEqual(width(result)['hardware']['canonical_value'],32)
        self.assertEqual(width(result)['software']['canonical_value'],32)
        self.assertEqual(sum(v['kind']=='required_parameter_mismatch' for v in result['findings']),2)
        self.assertNotIn('peer_parameter_mismatch',kinds(result))

    def test_stale_feature_depth_and_mode_have_separate_roles(self):
        for case,role in (('payload-feature-stale','feature'),('storage-depth-stale','depth'),('payload-mode-stale','mode')):
            result=review(*example(case));self.assertTrue(any(v.get('parameter')==role for v in result['findings']))

    def test_second_context_and_wider_storage_control(self):
        for case in ('storage-matched','storage-wide-matched'):
            values=example(case);self.assertEqual(exit_code(review(*values)),0)
            self.assertIn('CELL_BITS',values[0]['provenance']['selected_integral_parameters'])
            self.assertIn('CELL_BYTES',values[1]['provenance']['selected_constants'])

    def test_nonintegral_logical_width_is_not_rounded_to_carrier_storage(self):
        values=example('payload-nonintegral');self.assertEqual(values[0]['size_bits'],72)
        result=review(*values);self.assertEqual(width(result)['hardware']['raw_value'],66)
        self.assertIsNone(width(result)['hardware']['canonical_value']);self.assertIn('non_integral_unit_conversion',kinds(result))

    def test_missing_or_unknown_rule_is_not_automatic_unit_conversion(self):
        for variant in ('missing','unknown'):
            values=example('payload-matched')
            if variant=='missing':values[2]['parameters'][0]['software']['rule_ref']=None
            else:values[2]['unit_rules']['bytes-to-bits'].update(kind='unknown',numerator=None,denominator=None)
            result=review(*values);self.assertEqual(exit_code(result),2);self.assertIsNone(width(result)['software']['canonical_value'])

    def test_unknown_intent_is_not_derived_from_agreeing_captures(self):
        values=example('payload-matched');values[2]['parameters'][0]['required_value']=None
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIn('required_value_unknown',kinds(result,'gaps'))

    def test_unknown_units_remain_gaps_despite_equal_numbers(self):
        values=example('payload-matched');values[2]['parameters'][0]['hardware']['unit']=None
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIsNone(width(result)['hardware']['canonical_value'])

    def test_foreign_configuration_is_not_fixed_by_rebinding_only_hash(self):
        values=example('payload-matched');values[0]['configuration_ref']='other-mode';bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertFalse(result['views']['hardware']['binding_matches'])
        self.assertIsNone(width(result)['hardware']['raw_value'])

    def test_stale_export_digest_does_not_supply_changed_values(self):
        values=example('payload-matched');values[0]['provenance']['selected_integral_parameters']['WORD_BITS']=32
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIsNone(width(result)['hardware']['raw_value'])

    def test_source_override_context_cannot_migrate_by_label(self):
        values=example('payload-matched');values[0]['provenance']['requested_parameters']['WORD_BITS']=32;bind(values)
        result=review(*values);self.assertIn('source_context_binding_mismatch',kinds(result,'gaps'))

    def test_phase_and_native_frontend_limits_remain_explicit(self):
        for variant in ('phase','frontend'):
            values=example('payload-matched')
            if variant=='phase':values[0]['provenance']['fact_phase']=values[2]['views']['hardware']['fact_phase']='formal'
            else:
                values[0]['provenance']['fact_kind']=values[2]['views']['hardware']['fact_kind']='native'
                values[0]['frontend_ref']=values[2]['views']['hardware']['frontend_ref']='unqualified-tool'
            bind(values);result=review(*values);self.assertEqual(exit_code(result),2)

    def test_missing_resolved_capture_never_uses_requested_or_textual_parameters(self):
        values=example('payload-matched');del values[0]['provenance']['selected_integral_parameters'];bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIsNone(width(result)['hardware']['raw_value'])

    def test_unknown_single_fact_preserves_other_observations(self):
        values=example('payload-matched');values[0]['provenance']['selected_integral_parameters']['WORD_BITS']=None;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2)
        self.assertEqual(result['parameters'][1]['observations']['hardware']['canonical_value'],16)

    def test_known_mismatch_retains_other_missing_or_incomplete_evidence(self):
        values=example('payload-stale-default');values[0]['inputs_complete']=False;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),1);self.assertTrue(result['gaps'])

    def test_configuration_selection_is_not_whole_layout_or_all_parameters(self):
        values=example('payload-matched');values[1]['fields_complete']=False;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),0)
        self.assertEqual(result['views']['software']['fact_kind'],'reference-fixture')

    def test_contract_cannot_silently_alias_two_roles_to_one_fact(self):
        values=example('payload-matched');values[2]['parameters'][1]['hardware']['fact_ref']='WORD_BITS'
        with self.assertRaises(ValueError):review(*values)

    def test_empty_or_six_role_contract_and_boolean_values_are_invalid(self):
        for variant in ('empty','six','boolean','expression'):
            values=example('payload-matched')
            if variant=='empty':values[2]['parameters']=[]
            elif variant=='six':values[2]['parameters']*=2
            elif variant=='boolean':values[2]['parameters'][0]['required_value']=True
            else:values[2]['unit_rules']['bytes-to-bits']['kind']='eval(expression)'
            with self.assertRaises(ValueError):review(*values)

    def test_non_octet_identity_and_fractional_scales_not_guessed(self):
        values=example('payload-matched');values[2]['unit_rules']['bytes-to-bits'].update(kind='identity',numerator=1,denominator=1)
        with self.assertRaises(ValueError):review(*values)

    def test_cli_strict_json_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for key,value in zip(('hardware','software','contract'),example('payload-matched')):save(folder/(key+'.json'),value)
            command=[sys.executable,str(PROFILE/'configuration_review.py')]+[str(folder/(key+'.json')) for key in ('hardware','software','contract')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0)
            before=(folder/'hardware.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'hardware.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'hardware.json').read_bytes(),before)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(sys.platform=='linux' and os.environ.get('OPENTOOLS_CONFIG_NATIVE')=='1','Native Slang/GCC recipe not configured')
    def test_native_generated_defaults_units_and_consumer_values(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof');self.assertEqual(len(result['cases']),10)
            self.assertEqual(sum(c['status']=='within_selected_contract' for c in result['cases']),3)

@unittest.skipUnless(importlib.util.find_spec('pyslang'),'Slang optional dependency not installed')
class ParameterCaptureTests(unittest.TestCase):
    def test_actual_default_override_local_parameter_and_signed_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);source=folder/'facts.sv';source.write_text('module probe #(parameter int A=4); localparam int B=A*8, NEG=-2; typedef struct packed {logic[7:0] anchor;} t; endmodule')
            result=hardware([str(source)],[],'probe','t',{'A':8},'probe','current',True,folder/'hw',observed_parameters=['A','B','NEG'])
            self.assertEqual(result['provenance']['selected_integral_parameters'],{'A':8,'B':64,'NEG':-2})

    def test_missing_unknown_nonintegral_and_unbounded_selection_rejected(self):
        cases=(('parameter int A=4','MISSING'),("parameter logic[7:0] A=8'bx",'A'),('parameter real A=1.5','A'))
        for declaration,name in cases:
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary);source=folder/'bad.sv';source.write_text('module probe #('+declaration+'); typedef struct packed {logic[7:0] anchor;} t; endmodule')
                with self.assertRaises(ValueError):hardware([str(source)],[],'probe','t',{},'probe','current',True,folder/'hw',observed_parameters=[name])
        for selection in ([],['A']*2,['A','B','C','D','E','F'],['A+1']):
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(ValueError):hardware([str(MODULE/'examples/descriptor.sv')],[],'descriptor_top','descriptor_t',{},'probe','current',True,Path(temporary)/'hw',observed_parameters=selection)

@unittest.skipUnless(sys.platform=='linux' and shutil.which('gcc'),'Qualified GCC Linux required')
class ConstantCaptureTests(unittest.TestCase):
    def test_defaults_and_selected_constants_are_separate_from_field_encodings(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);header=folder/'facts.h';header.write_text('#include <stdint.h>\n#ifndef WIDTH\n#define WIDTH 4\n#endif\n#define NEGATIVE -3\nstruct probe{uint32_t anchor;};\n')
            result=software(str(header),[],'probe',{'fields':[{'name':'anchor'}],'defines':{}},'gcc','probe','current',True,True,folder/'sw',constants=['WIDTH','NEGATIVE'])
            self.assertEqual(result['provenance']['selected_constants'],{'WIDTH':4,'NEGATIVE':-3})
            self.assertFalse(result['fields'][0]['enum_values'])

    def test_nonintegral_runtime_and_out_of_range_constants_rejected(self):
        for declaration in ('#define BAD 1.5','static long long BAD=3;','#define BAD (((__int128)1)<<80)'):
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary);header=folder/'bad.h';header.write_text('#include <stdint.h>\n'+declaration+'\nstruct probe{uint32_t anchor;};\n')
                with self.assertRaises(ValueError):software(str(header),[],'probe',{'fields':[{'name':'anchor'}],'defines':{}},'gcc','probe','current',True,True,folder/'sw',constants=['BAD'])

if __name__=='__main__':unittest.main()
