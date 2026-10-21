# Collect a loaded physical supply and its selected library operating point.
proc opentools_supply_string {value} {
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
proc opentools_supply_record {stream args} {
    set fields {}
    foreach value $args {lappend fields [opentools_supply_string $value]}
    puts $stream "\[[join $fields ,]\]"
}
proc opentools_export_supply {run_ref net_name library_cell output_file database_file} {
    if {[file exists $output_file] || [file exists $database_file]} {error "Choose new output paths"}
    set block [ord::get_db_block];set net [$block findNet $net_name]
    if {$net == "NULL"} {error "Selected supply net missing"}
    set selected {}
    foreach cell [get_lib_cells *] {if {[get_full_name $cell] eq $library_cell} {lappend selected $cell}}
    if {[llength $selected] != 1} {error "Select one fully qualified library cell"}
    set cell [lindex $selected 0];set library [sta::LibertyCell_liberty_library $cell]
    set stream [open $output_file {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_supply_record $stream HEADER opentools.supply-native.v1 $run_ref $net_name
        opentools_supply_record $stream UNITS [[[ord::get_db] getTech] getDbUnitsPerMicron]
        opentools_supply_record $stream NET [$net getName] [$net getSigType]
        foreach term [$net getITerms] {
            set inst [$term getInst];set pin [$term getMTerm]
            opentools_supply_record $stream ITERM [$inst getName] [$pin getName] [$pin getSigType] [[$inst getMaster] getName] [$inst getPlacementStatus] {*}[$term getAvgXY]
        }
        foreach term [$net getBTerms] {opentools_supply_record $stream BTERM [$term getName] [$term getSigType]}
        foreach wire [$net getSWires] {
            foreach rect [$wire getWires] {
                if {[$rect isVia]} {opentools_supply_record $stream VIA [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]} else {
                    opentools_supply_record $stream SHAPE [[$rect getTechLayer] getName] [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]
                }
            }
        }
        opentools_supply_record $stream LIBRARY [sta::LibertyLibrary_name $library] [sta::LibertyCell_name $cell]
        set point [sta::LibertyLibrary_default_operating_conditions $library]
        if {$point == "NULL"} {opentools_supply_record $stream NO_OPERATING_POINT} else {
            opentools_supply_record $stream OPERATING_POINT [sta::OperatingConditions_process $point] [sta::OperatingConditions_voltage $point] [sta::OperatingConditions_temperature $point]
        }
        write_db $database_file
        opentools_supply_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_SUPPLY_EXPORT_COMPLETE
}
