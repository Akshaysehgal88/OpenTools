# Owned single-pass definitions. Archived constraints are never executed by Python.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
source trace_clocks.tcl
if {$trace_enabled} {opentools_clock_trace_start}
create_clock -name $root_name -period $root_period [get_ports $root_port]
foreach generator $generators {
    lassign $generator name target reference kind master divide
    set source [expr {$kind eq "port" ? [get_ports $reference] : [get_pins $reference]}]
    set options [list -name $name -source $source -divide_by $divide]
    if {$master ne "NONE"} {lappend options -master_clock $master}
    create_generated_clock {*}$options [get_pins $target]
}
if {$trace_enabled} {opentools_clock_trace_end}
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
set_input_delay 0.2 -clock $root_name [get_ports $data_port]
if {$propagate} {set_propagated_clock [all_clocks]}
source export_clocks.tcl
opentools_export_clocks $run_ref $inspected_case_ports $endpoint native.jsonl native.odb
write_sdc consumed.sdc
report_clock_properties [all_clocks]
puts OPENTOOLS_STA_LINEAGE_RUN_COMPLETE
