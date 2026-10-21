proc opentools_scenario_string {value} {
    set encoded ""
    foreach char [split $value ""] {
        scan $char %c code
        switch $code {
            34 {append encoded {\"}}
            92 {append encoded {\\}}
            9 {append encoded {\t}}
            10 {append encoded {\n}}
            13 {append encoded {\r}}
            default {if {$code<32} {error "Unsupported control character"};append encoded $char}
        }
    }
    return [format {"%s"} $encoded]
}
proc opentools_scenario_record {stream args} {
    set fields {};foreach v $args {lappend fields [opentools_scenario_string $v]};puts $stream "\[[join $fields ,]\]"
}
proc opentools_export_scenario {run_ref case_ports from_cell to_cell} {
    set libraries [get_libs *]
    if {[llength $libraries]!=1} {error "Qualify one library per native scenario process"}
    set library [lindex $libraries 0];set default [sta::LibertyLibrary_default_operating_conditions $library]
    if {$default eq "NULL"} {error "Explicit library operating condition required"}
    set stream [open native.jsonl {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_scenario_record $stream HEADER opentools.sta-scenario-native.v1 $run_ref
        opentools_scenario_record $stream LIBRARY [get_full_name $library] [sta::OperatingConditions_process $default] [sta::OperatingConditions_voltage $default] [sta::OperatingConditions_temperature $default]
        foreach selector {min max} {
            set condition [sta::operating_conditions $selector]
            if {$condition eq "NULL"} {error "Effective operating condition missing"}
            opentools_scenario_record $stream OPERATING $selector [sta::OperatingConditions_process $condition] [sta::OperatingConditions_voltage $condition] [sta::OperatingConditions_temperature $condition] [expr {$condition eq $default}]
        }
        foreach port $case_ports {
            set pin [get_ports $port];if {[llength $pin]!=1} {error "Case port missing/ambiguous"}
            opentools_scenario_record $stream CASE $port [sta::pin_case_logic_value [sta::get_port_pin $pin]]
        }
        foreach clock [all_clocks] {
            set name [get_full_name $clock]
            opentools_scenario_record $stream CLOCK $name [get_property $clock period] [get_property $clock is_propagated]
            foreach pin [get_property $clock sources] {opentools_scenario_record $stream SOURCE $name [get_full_name $pin]}
            foreach pin [all_registers -clock $clock -clock_pins] {opentools_scenario_record $stream COVERAGE $name [get_full_name $pin]}
        }
        foreach {option tag} {clock_pins CLOCK_PIN data_pins DATA_PIN output_pins OUTPUT_PIN} {
            foreach pin [all_registers -$option] {opentools_scenario_record $stream $tag [get_full_name $pin]}
        }
        set from [get_cells $from_cell];set to [get_cells $to_cell]
        if {[llength $from]!=1 || [llength $to]!=1} {error "Select one scalar launch/capture instance pair"}
        set paths [find_timing_paths -from $from -to $to -path_delay max -group_count 20]
        opentools_scenario_record $stream PATH_COUNT [llength $paths]
        foreach path $paths {opentools_scenario_record $stream PATH [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]] [get_property $path slack]}
        write_db native.odb
        write_sdc consumed.sdc
        opentools_scenario_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_SCENARIO_RC_BEGIN
    report_parasitic_annotation
    puts OPENTOOLS_SCENARIO_RC_END
    puts OPENTOOLS_STA_SCENARIO_RUN_COMPLETE
}
