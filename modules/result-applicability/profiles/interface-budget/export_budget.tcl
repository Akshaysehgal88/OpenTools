proc opentools_budget_string {value} {
    set out ""
    foreach char [split $value ""] {
        scan $char %c code
        switch $code {
            34 {append out {\"}}
            92 {append out {\\}}
            9 {append out {\t}}
            10 {append out {\n}}
            13 {append out {\r}}
            default {if {$code<32} {error "Unsupported control character"};append out $char}
        }
    }
    return [format {"%s"} $out]
}
proc opentools_budget_record {stream args} {
    set fields {};foreach v $args {lappend fields [opentools_budget_string $v]};puts $stream "\[[join $fields ,]\]"
}
proc opentools_budget_point {kind name} {
    if {$kind eq "port"} {set point [get_ports $name]} else {set point [get_pins $name]}
    if {[llength $point]!=1} {error "Select exactly one native point"};return $point
}
proc opentools_export_budget {} {
    global run_ref view inspected_cases from_kind from to_kind to output_port bridge_net sink_net
    set start [opentools_budget_point $from_kind $from];set finish [opentools_budget_point $to_kind $to]
    report_checks -from $start -to $finish -path_delay max -group_count 1 -format full_clock_expanded -digits 6 > path.txt
    puts OPENTOOLS_BUDGET_UNITS_BEGIN
    report_units
    puts OPENTOOLS_BUDGET_UNITS_END
    if {$bridge_net ne "NONE"} {report_net -digits 6 $bridge_net > bridge-net.txt} else {close [open bridge-net.txt {WRONLY CREAT EXCL}]}
    if {$sink_net ne "NONE"} {report_net -digits 6 $sink_net > sink-net.txt} else {close [open sink-net.txt {WRONLY CREAT EXCL}]}
    set stream [open native.jsonl {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_budget_record $stream HEADER opentools.interface-budget-native.v1 $run_ref $view
        foreach library [get_libs *] {opentools_budget_record $stream LIBRARY [get_full_name $library]}
        foreach selector {min max} {
            set condition [sta::operating_conditions $selector]
            if {$condition eq "NULL"} {error "Explicit selected operating condition required"}
            opentools_budget_record $stream PVT $selector [sta::OperatingConditions_process $condition] [sta::OperatingConditions_voltage $condition] [sta::OperatingConditions_temperature $condition]
        }
        foreach clock [all_clocks] {
            set name [get_full_name $clock]
            opentools_budget_record $stream CLOCK $name [get_property $clock period]
            set wave {};foreach edge [sta::Clock_waveform $clock] {lappend wave [sta::format_time $edge 6]}
            opentools_budget_record $stream WAVE $name {*}$wave
            foreach pin [get_property $clock sources] {opentools_budget_record $stream SOURCE $name [get_full_name $pin]}
        }
        foreach port $inspected_cases {opentools_budget_record $stream CASE $port [sta::pin_case_logic_value [sta::get_port_pin [get_ports $port]]]}
        if {$output_port ne "NONE"} {
            foreach selector {min max} {
                opentools_budget_record $stream PORT_CAP $selector [sta::format_capacitance [sta::port_ext_pin_cap [get_ports $output_port] [sta::cmd_corner] $selector] 6] [sta::format_capacitance [sta::port_ext_wire_cap [get_ports $output_port] [sta::cmd_corner] $selector] 6]
            }
        }
        # A subsequent report search can invalidate PathEnd handles. Acquire
        # them after all reporting and consume them before another search.
        set paths [find_timing_paths -from $start -to $finish -path_delay max -group_count 1]
        opentools_budget_record $stream PATH_COUNT [llength $paths]
        foreach path $paths {
            set edge [sta::PathEnd_target_clk_edge $path]
            opentools_budget_record $stream PATH [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]] [get_property $path slack] [sta::format_time [sta::PathEnd_data_arrival_time $path] 6] [sta::format_time [sta::PathEnd_data_required_time $path] 6] [sta::format_time [sta::PathEnd_margin $path] 6] [sta::format_time [sta::PathEnd_target_clk_time $path] 6] [sta::format_time [sta::ClockEdge_time $edge] 6] [sta::ClockEdge_transition $edge] [sta::PathEnd_is_output_delay $path] [sta::PathEnd_is_check $path]
        }
        set block [ord::get_db_block]
        foreach inst [$block getInsts] {
            set name [$inst getName]
            opentools_budget_record $stream CELL $name [[$inst getMaster] getName]
            foreach term [$inst getITerms] {
                set net [$term getNet];set net_name "";if {$net ne "NULL"} {set net_name [$net getName]}
                opentools_budget_record $stream PIN $name/[[$term getMTerm] getName] [[$term getMTerm] getIoType] $net_name
            }
        }
        foreach term [$block getBTerms] {set net [$term getNet];set name "";if {$net ne "NULL"} {set name [$net getName]};opentools_budget_record $stream PORT [$term getName] [$term getIoType] $name}
        write_db native.odb
        write_sdc consumed.sdc
        opentools_budget_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_INTERFACE_BUDGET_RUN_COMPLETE
}
