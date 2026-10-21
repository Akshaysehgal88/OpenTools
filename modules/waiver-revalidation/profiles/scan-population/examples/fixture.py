"""Owned single-clock and mixed-clock qualification contexts for scan closure."""
import json
FAMILIES={
 'control-bank':{'module':'control_partition','width':4,'prefix':'ff','data':'data','q':'q','clocks':['clk'],'reset':'reset_n'},
 'mixed-bank':{'module':'state_partition','width':8,'prefix':'state','data':'payload','q':'status','clocks':['core_clock','retained_clock'],'reset':'clear_n'}}
CASES=('complete','missing-required','allowed-exclusion','obsolete-role','missing-rationale','wrong-clock-group','stale-exclusion','partial-roster')
def clock(c,i,case):
    if len(c['clocks'])==1:return c['clocks'][0]
    if i==0 and case=='obsolete-role':return c['clocks'][0]
    return c['clocks'][int(i<c['width']//2)]
def seed(c,case):
    ports=c['clocks']+[c['reset'],c['data'],c['q']];w=c['width']
    lines=[f"module {c['module']}("+', '.join(ports)+');']+['input '+v+';' for v in ports[:-2]]+[f"input [{w-1}:0] {c['data']};",f"output [{w-1}:0] {c['q']};"]
    lines += [f"DFFR_CELL {c['prefix']}{i} (.CK({clock(c,i,case)}),.RN({c['reset']}),.D({c['data']}[{i}]),.Q({c['q']}[{i}]));" for i in range(w)]
    return '\n'.join(lines+['endmodule',''])
def selections(family,case):
    c=FAMILIES[family];base='owned/'+family;configuration=base+'/'+('retained-role' if case=='allowed-exclusion' else 'current-role')
    context={'format':'opentools.scan-context.v1','run_ref':family+'-'+case,'scope':base,'design_ref':base+'/netlist','configuration_ref':configuration,'population_ref':base+'/required-state-r1','module':c['module'],'functional_master':'DFFR_CELL','scan_master':'SCANR_CELL','pins':{'clock':'CK','reset':'RN','data':'D','state':'Q','scan_in':'SI','enable':'SE'},'mapping_basis_ref':base+'/source-pin-map','library_basis_ref':base+'/owned-cell-semantics','power_basis_ref':base+'/logical-group-intent'}
    states=[]
    for i in range(c['width']):
        allowed=i==0 and case in ('allowed-exclusion','missing-rationale','stale-exclusion')
        states.append({'id':base+'/state-'+str(i),'instance':c['prefix']+str(i),'scan_required':not allowed,'role':'retained' if allowed else 'functional','clock':('other_clock' if i==0 and case=='wrong-clock-group' else clock(c,i,case)),'power_group':'retained-logic' if len(c['clocks'])>1 and clock(c,i,case)==c['clocks'][1] else 'main-logic','basis_ref':base+'/state-intent/'+str(i)})
    population={'format':'opentools.scan-population.v1',**{k:context[k] for k in ('scope','design_ref','configuration_ref','population_ref')},'source_ref':base+'/independent-required-population','complete':True,'states':states[:-1] if case=='partial-roster' else states}
    exclusions=[]
    if case in ('allowed-exclusion','obsolete-role','missing-rationale','stale-exclusion'):
        old_clock=clock(c,0,'allowed-exclusion')
        exclusions=[{'id':'retained-state','instance':c['prefix']+'0','reason':'Retained-only state is permitted outside this selected scan population.','rationale_revision':None if case=='missing-rationale' else base+'/retained-policy-r1','approval_ref':base+'/fixture-policy-owner','basis_ref':base+'/retained-policy-source','required_role':'retained','required_clock':old_clock,'required_power_group':'retained-logic' if len(c['clocks'])>1 else 'main-logic'}]
    policy={'format':'opentools.scan-exclusions.v1',**{k:context[k] for k in ('scope','design_ref','configuration_ref','population_ref')},'records':exclusions}
    if case=='stale-exclusion':policy['configuration_ref']=base+'/older-configuration'
    protected=[c['prefix']+'0'] if case in ('missing-required','allowed-exclusion','obsolete-role','missing-rationale','stale-exclusion') else []
    return context,population,policy,protected
def flow(c,protected):
    lines=['read_verilog seed.v','read_lef cells.lef','read_liberty cells.lib','link_design '+c['module']]
    lines += [f'create_clock -name scan_{i} -period {10+i*10} [get_ports {name}]' for i,name in enumerate(c['clocks'])]
    lines += ['''proc export_inventory {stage file_name} {
  set output [open $file_name w]
  puts $output "FORMAT opentools.openroad-scan-inventory.v1 $stage"
  foreach cell [all_registers -cells] { puts $output "SEQ [get_full_name $cell]" }
  set block [ord::get_db_block]
  foreach instance [$block getInsts] {
    puts $output "CELL [$instance getName] [[$instance getMaster] getName]"
    foreach terminal [$instance getITerms] {
      set net [$terminal getNet]
      if {$net != "NULL"} { puts $output "PIN [$instance getName] [[$terminal getMTerm] getName] [$net getName]" }
    }
  }
  foreach port [$block getBTerms] { puts $output "PORT [$port getName] [$port getIoType] [[$port getNet] getName]" }
  puts $output "OPENTOOLS_NATIVE_INVENTORY_COMPLETE"
  close $output
}''','export_inventory PRE pre.txt','write_verilog -sort pre.v','write_db pre.odb']
    lines += ['set_dont_touch [get_cells '+name+']' for name in protected]
    lines += ['set_dft_config -max_length 32 -max_chains 32 -clock_mixing no_mix','report_dft_config','scan_replace','preview_dft -verbose','insert_dft','export_inventory POST post.txt','write_verilog -sort post.v','write_db post.odb','puts "OPENTOOLS_NATIVE_SCAN_POPULATION_COMPLETE"','exit','']
    return '\n'.join(lines)
