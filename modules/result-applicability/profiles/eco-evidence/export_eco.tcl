# Data comes from qualified config.tcl; no imported record is executed by review.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
create_clock -name $clock_name -period $period [get_ports $clock_port]
set_input_delay -clock $clock_name 0.2 [get_ports [list $data_a $data_b]]
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set output [open graph.txt {WRONLY CREAT EXCL}]
puts $output "FORMAT opentools.eco-graph.v1"
puts $output "RUN $run_ref"
foreach inst [$block getInsts] {
 puts $output "CELL [$inst getName] [[$inst getMaster] getName]"
 puts $output "PLACE [$inst getName] [$inst getOrient] [$inst getLocation] [$inst getPlacementStatus]"
 foreach term [$inst getITerms] {
  set net [$term getNet]
  puts $output "PIN [$inst getName] [[$term getMTerm] getName] [[$term getMTerm] getIoType] [[$term getMTerm] getSigType] [expr {$net == "NULL" ? "UNCONNECTED" : [$net getName]}]"
 }
}
foreach term [$block getBTerms] {puts $output "PORT [$term getName] [$term getIoType] [[$term getNet] getName]"}
puts $output END
close $output
set paths [find_timing_paths -to [get_cells $capture_cell] -path_delay max]
set output [open sta.txt {WRONLY CREAT EXCL}]
puts $output "FORMAT opentools.eco-sta.v1"
puts $output "RUN $run_ref"
set clock [get_clocks $clock_name]
puts $output "CLOCK $clock_name [get_property $clock period] [get_property $clock is_generated]"
set sources {}
foreach pin [get_property $clock sources] {lappend sources [get_full_name $pin]}
puts $output "CLOCK_SOURCES [llength $sources] [join $sources { }]"
puts $output "PATH_COUNT [llength $paths]"
foreach path $paths {
 puts $output "PATH [get_property $path slack] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]]"
}
foreach {port value} $phase_cases {
 puts $output "CASE $port [sta::pin_case_logic_value [sta::get_port_pin [get_ports $port]]]"
}
set names {}
foreach pin [all_registers -clock_pins] {lappend names [get_full_name $pin]}
puts $output "REGISTER_CLOCK_PINS [llength $names] [join $names { }]"
puts $output "PATH_RESULT [expr {[llength $paths] == 1 ? "PASS" : "FAIL"}]"
puts $output END
close $output
write_sdc consumed.sdc
report_checks -path_delay max -format full_clock_expanded
write_db design.odb
write_verilog exported.v
puts OPENTOOLS_ECO_NATIVE_COMPLETE
