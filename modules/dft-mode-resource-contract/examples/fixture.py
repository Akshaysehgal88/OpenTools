"""Owned native DFT fixtures; names and widths are application contexts, not tool IDs."""
import re

FAMILIES={
 'register-bank':{'width':4,'module':'scan_partition','clock':'clk','reset':'reset_n','data':'data','q':'q','prefix':'ff','period':10,'load':11,'capture':6},
 'status-bank':{'width':8,'module':'test_partition','clock':'shift_clk','reset':'clear_n','data':'payload','q':'state','prefix':'bit','period':20,'load':165,'capture':60}}
CASES={
 'reset-clamp':([0,1,0,1,0,1,1,1],'match'),
 'supported-mask':([1,1,0,1,0,1,1,1],'match'),
 'debug-is-not-manufacturing':([1,0,1,1,0,1,1,1],'match'),
 'manufacturing-denied':([1,0,0,1,0,1,1,1],'match'),
 'power-unavailable':([1,1,0,0,0,1,1,1],'match'),
 'isolated-output':([1,1,0,1,1,1,1,1],'match'),
 'wrong-clock':([1,1,0,1,0,0,1,1],'match'),
 'wrong-capture-enable':([1,1,0,1,0,1,0,1],'match'),
 'functional-control':([1,1,1,1,0,1,1,0],'match'),
 'authorized-debug-enabled':([1,1,1,1,0,1,1,1],'match'),
 'constraint-reset-asserted':([1,1,0,1,0,1,1,1],'asserted'),
 'constraint-reset-unknown':([1,1,0,1,0,1,1,1],'unknown')}
INPUT_ROLES=('fclk','tclk','por','functional_reset','test_mode','manufacturing','debug','power','isolation','shift_request','serial_in','parallel_data')
OUTPUT_ROLES=('reset_level','scan_enable','chain_clock','raw_state','visible_state','serial_out')
def roles(family):
    first=dict(zip(INPUT_ROLES+OUTPUT_ROLES,('functional_clock','test_clock','power_on_reset','functional_reset','test_mode','manufacturing_allow','functional_debug_allow','power_ready','isolation','shift_request','serial_in','parallel_data','effective_reset_n','effective_scan_enable','chain_clock','raw_state','visible_state','serial_out')))
    return first if family=='register-bank' else {k:'port_'+v for k,v in first.items()}
def seed(c):
    w=c['width'];lines=[f"module {c['module']}({c['clock']}, {c['reset']}, {c['data']}, {c['q']});",f"input {c['clock']};",f"input {c['reset']};",f"input [{w-1}:0] {c['data']};",f"output [{w-1}:0] {c['q']};"]
    lines += [f"DFFR_CELL {c['prefix']}{i} (.CK({c['clock']}),.RN({c['reset']}),.D({c['data']}[{i}]),.Q({c['q']}[{i}]));" for i in range(w)]
    return '\n'.join(lines+['endmodule',''])
def dft_script(c):
    return f'''read_verilog seed.v
read_lef cells.lef
read_liberty cells.lib
link_design {c['module']}
create_clock -name scan_clock -period {c['period']} [get_ports {c['clock']}]
set_dft_config -max_length {c['width']} -max_chains 1 -clock_mixing no_mix
report_dft_config
scan_replace
write_verilog -sort replaced.v
preview_dft -verbose
insert_dft
write_verilog -sort scanned.v
write_db scanned.odb
write_def scanned.def
puts "OPENTOOLS_NATIVE_DFT_COMPLETE"
exit
'''
def mode_sdc(c,flags,kind):
    mask,mfg,debug,power,iso,drive,capture_correct,test=flags;reset=int(bool(mask and mfg and test))
    if kind=='asserted':reset=0
    reset_value='X' if kind=='unknown' else str(reset)
    modes={'shift':(reset_value,str(int(bool(test and mfg)))),'capture':(reset_value,str(int(bool(test and mfg and not capture_correct)))),'unload':(reset_value,str(int(bool(test and mfg))))}
    lines=[f"create_clock -name scan_clock -period {c['period']} [get_ports {c['clock']}]",'proc opentools_mode {phase} {','  switch -- $phase {']
    for phase,(r,e) in modes.items():
        reset_cmd=f"unset_case_analysis [get_ports {c['reset']}]" if r=='X' else f"set_case_analysis {r} [get_ports {c['reset']}]"
        lines += [f"    {phase} {{ {reset_cmd}; set_case_analysis {e} [get_ports scan_enable_1] }}"]
    return '\n'.join(lines+['    default { error "Unknown owned phase" }','  }','}',''])
def export_script(c):
    return f'''read_verilog scanned.v
read_lef cells.lef
read_liberty cells.lib
link_design {c['module']}
source mode.sdc
set output [open resources.txt w]
puts $output "FORMAT opentools.openroad-dft-resources.v1"
puts $output "MODULE {c['module']}"
foreach clock [get_clocks scan_clock] {{ puts $output "CLOCK scan_clock [get_property $clock period]" }}
set block [ord::get_db_block]
foreach instance [$block getInsts] {{
  puts $output "CELL [$instance getName] [[$instance getMaster] getName]"
  foreach terminal [$instance getITerms] {{
    set net [$terminal getNet]
    if {{$net != "NULL"}} {{ puts $output "PIN [$instance getName] [[$terminal getMTerm] getName] [$net getName]" }}
  }}
}}
foreach port [$block getBTerms] {{ puts $output "PORT [$port getName] [$port getIoType] [[$port getNet] getName]" }}
foreach phase {{shift capture unload}} {{
  opentools_mode $phase
  foreach name {{{c['reset']} scan_enable_1}} {{
    set pin [sta::get_port_pin [get_ports $name]]
    puts $output "CASE $phase $name [sta::pin_case_logic_value $pin]"
  }}
  sta::find_logic_constants
  foreach pin [get_pins {c['prefix']}0/RN] {{ puts $output "LEAF_SIM $phase {c['prefix']}0/RN [sta::pin_sim_logic_value $pin]" }}
}}
puts $output "OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE"
close $output
puts "OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE"
exit
'''
def topology(text,c):
    pins={};ports={}
    for line in text.splitlines():
        p=line.split()
        if p and p[0]=='CELL':pins[p[1]]={}
        elif p and p[0]=='PIN':pins[p[1]][p[2]]=p[3]
        elif p and p[0]=='PORT':ports[p[1]]=p[3]
    lookup={p['SI']:n for n,p in pins.items()};net=ports['scan_in_1'];order=[];positions=[]
    while net in lookup:
        n=lookup[net]
        if n in order:raise ValueError('Native scan cycle')
        order.append(n);net=pins[n]['Q'];m=re.fullmatch(re.escape(c['q'])+r'\[(\d+)\]',net)
        if m is None:raise ValueError('Owned fixture output bit not explicit')
        positions.append(int(m[1]))
    if len(order)!=c['width'] or net not in ports.values():raise ValueError('Native chain does not span the owned fixture')
    return order,positions,net
def wrapper(family,c,stop):
    m=roles(family);w=c['width'];inputs=[];outputs=[]
    for r in INPUT_ROLES:inputs.append(('input '+(f'[{w-1}:0] ' if r=='parallel_data' else '')+m[r]))
    for r in OUTPUT_ROLES:outputs.append(('output '+(f'[{w-1}:0] ' if r in ('raw_state','visible_state') else '')+m[r]))
    lines=['module top('+',\n  '.join(inputs+['input fixture_reset_mask']+outputs)+');',f"wire allowed = {m['test_mode']} && {m['manufacturing']};",
      f"assign {m['chain_clock']} = ({m['test_mode']} ? {m['tclk']} : {m['fclk']}) && {m['power']} && (!{m['test_mode']} || {m['manufacturing']});",
      f"assign {m['reset_level']} = !({m['por']} || ({m['functional_reset']} && !(allowed && fixture_reset_mask)));",
      f"assign {m['scan_enable']} = allowed && {m['shift_request']};",
      f"{c['module']} dut (.{c['clock']}({m['chain_clock']}),.{c['reset']}({m['reset_level']}),.{c['data']}({m['parallel_data']}),.{c['q']}({m['raw_state']}),.scan_enable_1({m['scan_enable']}),.scan_in_1({m['serial_in']}));",
      f"assign {m['visible_state']} = {m['isolation']} ? {w}'b0 : {m['raw_state']};"]
    bit=int(re.fullmatch(re.escape(c['q'])+r'\[(\d+)\]',stop)[1]);lines += [f"assign {m['serial_out']} = {m['isolation']} ? 1'b0 : {m['raw_state']}[{bit}];",'endmodule','']
    return '\n'.join(lines)
def header(family,c,positions):
    return ''.join('#define P_'+k.upper()+' '+v+'\n' for k,v in roles(family).items())+f"#define WIDTH {c['width']}\n#define LOAD_WORD {c['load']}\n#define CAPTURE_WORD {c['capture']}\nstatic const unsigned SCAN_BITS[WIDTH] = {{"+','.join(map(str,positions))+'};\n'
