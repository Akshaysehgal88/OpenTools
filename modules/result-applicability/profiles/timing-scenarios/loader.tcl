# Fresh single-library setup analysis; no inherited SDC, parasitics or exceptions.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
set_operating_conditions $operating_condition
create_clock -name $clock_name -period $period_ns [get_ports $clock_port]
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
set_propagated_clock [all_clocks]
source export_scenario.tcl
opentools_export_scenario $run_ref $inspected_cases $from_cell $to_cell
