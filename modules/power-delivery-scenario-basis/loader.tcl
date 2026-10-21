# Explicit static loads/sources. Solver completion is not an IR acceptance verdict.
source config.tcl
read_lef cells.lef
read_liberty cells.lib
read_def design.def
foreach {layer value} $layer_resistance {set_layer_rc -layer $layer -resistance $value -capacitance 0.0 -corner $corner}
set_pdnsim_net_voltage -net $net -voltage $net_voltage -corner $corner
foreach {inst value} $instance_power {set_pdnsim_inst_power -inst $inst -power $value -corner $corner}
source export_supply.tcl
opentools_export_supply $run_ref $net $library_cell native.jsonl native.odb
set stream [open status.jsonl {WRONLY CREAT EXCL}]
fconfigure $stream -encoding utf-8 -translation lf
opentools_supply_record $stream HEADER opentools.supply-status.v1 $run_ref
set code [catch {check_power_grid -net $net -error_file connectivity.rpt} message]
opentools_supply_record $stream STATUS connectivity $code $message
set code [catch {analyze_power_grid -net $net -corner $corner -vsrc sources.csv -voltage_file voltage.csv -error_file errors.rpt} message]
opentools_supply_record $stream STATUS analysis $code $message
set code [catch {write_pg_spice -net $net -corner $corner -vsrc sources.csv network.sp} message]
opentools_supply_record $stream STATUS spice $code $message
opentools_supply_record $stream END
close $stream
puts OPENTOOLS_SUPPLY_RUN_COMPLETE
