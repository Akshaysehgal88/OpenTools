# One fresh flat scalar mode; no imported constraints, exceptions or parasitics.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
create_clock -name $clock_name -period $period_ns [get_ports $clock_port]
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
foreach {port value} $input_delays {set_input_delay $value -clock $clock_name [get_ports $port]}
foreach {port value} $output_delays {set_output_delay $value -clock $clock_name [get_ports $port]}
set_propagated_clock [all_clocks]
source export_endpoints.tcl
opentools_export_endpoints $run_ref $inspected_cases
