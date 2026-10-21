# Owned batch loader. The exporter can also be sourced in an existing native flow.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design $top
initialize_floorplan -die_area $die_um -core_area $core_um -site $site
foreach placement $placements {
    lassign $placement name x y orientation
    set inst [[ord::get_db_block] findInst $name]
    if {$inst == "NULL"} {error "Placement instance missing"}
    $inst setOrient $orientation
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
}
foreach rect $blockages {odb::dbBlockage_create [ord::get_db_block] {*}$rect}
create_clock -name $clock_name -period $period_ns [get_ports $clock_port]
set_input_delay 0.2 -clock $clock_name [get_ports $data_ports]
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
set_propagated_clock [get_clocks $clock_name]
source export_region.tcl
opentools_export_region $run_ref $selected_net $endpoint $clock_name [dict keys $phase_cases] native.jsonl native.odb
write_sdc consumed.sdc
