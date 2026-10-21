# Owned example: fixed explicit assumptions, not architectural-latency conversion.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
set_operating_conditions qualified
set options [list -name $clock_name -period $period_ns]
if {$clock_port eq "NONE"} {create_clock {*}$options} else {create_clock {*}$options [get_ports $clock_port]}
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
if {$input_port ne "NONE"} {set_input_delay $input_delay_ns -clock $clock_name [get_ports $input_port]}
if {$output_port ne "NONE"} {
    set options [list $output_delay_ns -clock $clock_name]
    if {$output_fall} {lappend options -clock_fall}
    set_output_delay {*}$options [get_ports $output_port]
    set_load $load_pF [get_ports $output_port]
}
if {$clock_port ne "NONE"} {set_propagated_clock [all_clocks]}
source export_budget.tcl
opentools_export_budget
