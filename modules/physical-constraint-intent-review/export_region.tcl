# Collect loaded native placement/constraint facts and the native placement check.
proc opentools_region_string {value} {
    set encoded ""
    foreach char [split $value ""] {
        scan $char %c code
        switch $code {
            34 {append encoded {\"}}
            92 {append encoded {\\}}
            9 {append encoded {\t}}
            10 {append encoded {\n}}
            13 {append encoded {\r}}
            default {if {$code < 32} {error "Unsupported control character"};append encoded $char}
        }
    }
    return [format {"%s"} $encoded]
}
proc opentools_region_record {stream args} {
    set fields {}
    foreach value $args {lappend fields [opentools_region_string $value]}
    puts $stream "\[[join $fields ,]\]"
}
proc opentools_export_region {run_ref selected_net endpoint clock_name case_ports output_file database_file} {
    if {[file exists $output_file] || [file exists $database_file]} {error "Choose new output paths"}
    set block [ord::get_db_block]
    set net [$block findNet $selected_net]
    if {$net == "NULL"} {error "Selected native net missing"}
    set clocks [get_clocks $clock_name]
    if {[llength $clocks] != 1 || [llength [get_pins $endpoint]] != 1} {error "Select exactly one clock and endpoint"}
    set stream [open $output_file {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_region_record $stream HEADER opentools.physical-native.v1 $run_ref $selected_net $endpoint
        opentools_region_record $stream UNITS [[[ord::get_db] getTech] getDbUnitsPerMicron]
        foreach {kind method} {DIE getDieArea CORE getCoreArea} {
            set rect [$block $method]
            opentools_region_record $stream $kind [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]
        }
        set clock [lindex $clocks 0]
        opentools_region_record $stream CLOCK [get_full_name $clock] [get_property $clock period] [get_property $clock is_generated]
        foreach source [get_property $clock sources] {opentools_region_record $stream CLOCK_SOURCE [get_full_name $source]}
        foreach port $case_ports {
            set native [get_ports $port]
            if {[llength $native] != 1} {error "Case port missing/ambiguous"}
            opentools_region_record $stream CASE $port [sta::pin_case_logic_value [sta::get_port_pin $native]]
        }
        foreach inst [$block getInsts] {
            set rect [$inst getBBox]
            opentools_region_record $stream INSTANCE [$inst getName] [[$inst getMaster] getName] [$inst getOrient] [$inst getPlacementStatus] [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]
            foreach term [$inst getITerms] {
                set net_obj [$term getNet];set net_name ""
                if {$net_obj != "NULL"} {set net_name [$net_obj getName]}
                opentools_region_record $stream PIN [$inst getName] [[$term getMTerm] getName] [[$term getMTerm] getIoType] [$term getSigType] $net_name {*}[$term getAvgXY]
            }
        }
        foreach port [$block getBTerms] {
            set net_obj [$port getNet];set net_name ""
            if {$net_obj != "NULL"} {set net_name [$net_obj getName]}
            opentools_region_record $stream PORT [$port getName] [$port getIoType] $net_name
        }
        foreach blockage [$block getBlockages] {
            set rect [$blockage getBBox]
            opentools_region_record $stream BLOCKAGE [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax] [$blockage isSoft]
        }
        set rect [$net getTermBBox]
        opentools_region_record $stream NET_BBOX [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]
        foreach term [$net getITerms] {opentools_region_record $stream NET_TERM [[$term getInst] getName] [[$term getMTerm] getName]}
        foreach port [$net getBTerms] {opentools_region_record $stream NET_BTERM [$port getName]}
        set paths [find_timing_paths -to [get_pins $endpoint] -path_delay max -group_count 20]
        opentools_region_record $stream PATH_COUNT [llength $paths]
        foreach path $paths {opentools_region_record $stream PATH [get_property $path slack] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]]}
        set code [catch {check_placement -verbose} problem]
        opentools_region_record $stream PLACEMENT_CHECK $code $problem
        write_db $database_file
        opentools_region_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_PHYSICAL_EXPORT_COMPLETE
}
