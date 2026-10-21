# Read one selected macro from the current OpenROAD database and timing library.
proc opentools_macro_json_string {value} {
    set encoded ""
    foreach char [split $value ""] {
        scan $char %c code
        switch $code {
            34 {append encoded {\"}}
            92 {append encoded {\\}}
            9 {append encoded {\t}}
            10 {append encoded {\n}}
            13 {append encoded {\r}}
            default {
                if {$code < 32} {error "Unsupported control character in native name"}
                append encoded $char
            }
        }
    }
    return [format {"%s"} $encoded]
}
proc opentools_macro_record {stream args} {
    set fields {}
    foreach value $args {lappend fields [opentools_macro_json_string $value]}
    puts $stream "\[[join $fields ,]\]"
}
proc opentools_export_macro {instance_name library_cell_name output_file database_file} {
    if {[file exists $output_file] || [file exists $database_file]} {error "Select new export and database paths"}
    set block [ord::get_db_block]
    set inst [$block findInst $instance_name]
    if {$inst == "NULL"} {error "Selected native instance not found"}
    set selected {}
    foreach cell [get_lib_cells *] {
        if {[get_full_name $cell] eq $library_cell_name} {lappend selected $cell}
    }
    if {[llength $selected] != 1} {error "Select exactly one fully qualified library cell"}
    set cell [lindex $selected 0]
    set master [$inst getMaster]
    set library [sta::LibertyCell_liberty_library $cell]
    set stream [open $output_file {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_macro_record $stream HEADER opentools.macro-native.v1
        opentools_macro_record $stream UNITS [[[ord::get_db] getTech] getDbUnitsPerMicron]
        opentools_macro_record $stream INSTANCE [$inst getName] [$master getName] [$inst getOrient] {*}[$inst getLocation] [$inst getPlacementStatus]
        opentools_macro_record $stream MASTER [$master getWidth] [$master getHeight] [$master getSymmetryX] [$master getSymmetryY] [$master getSymmetryR90]
        set bounds [$inst getBBox]
        opentools_macro_record $stream INSTANCE_BOX [$bounds xMin] [$bounds yMin] [$bounds xMax] [$bounds yMax]
        foreach term [$master getMTerms] {
            opentools_macro_record $stream MTERM [$term getName] [$term getIoType] [$term getSigType]
            foreach pin [$term getMPins] {
                foreach box [$pin getGeometry] {
                    opentools_macro_record $stream PIN_BOX [$term getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]
                }
            }
        }
        foreach box [$master getObstructions] {
            opentools_macro_record $stream OBS [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]
        }
        foreach terminal [$inst getITerms] {
            set net [$terminal getNet]
            if {$net == "NULL"} {set net_name "";set net_type ""} else {set net_name [$net getName];set net_type [$net getSigType]}
            opentools_macro_record $stream ITERM [[$terminal getMTerm] getName] [$terminal getSigType] $net_name $net_type
        }
        opentools_macro_record $stream LIBRARY [sta::LibertyLibrary_name $library] [sta::LibertyCell_name $cell]
        set condition [sta::LibertyLibrary_default_operating_conditions $library]
        if {$condition == "NULL"} {
            opentools_macro_record $stream NO_OPERATING_POINT
        } else {
            opentools_macro_record $stream OPERATING_POINT [sta::OperatingConditions_process $condition] [sta::OperatingConditions_voltage $condition] [sta::OperatingConditions_temperature $condition]
        }
        set iterator [sta::LibertyCell_liberty_port_iterator $cell]
        while {[sta::LibertyCellPortIterator_has_next $iterator]} {
            set port [sta::LibertyCellPortIterator_next $iterator]
            opentools_macro_record $stream LIBPIN [get_property $port name] [get_property $port direction] [sta::LibertyPort_is_bus $port]
        }
        sta::LibertyCellPortIterator_finish $iterator
        foreach arc [sta::LibertyCell_timing_arc_sets $cell] {
            set from [sta::TimingArcSet_from $arc];set to [sta::TimingArcSet_to $arc]
            set from_name "";set to_name ""
            if {$from != "NULL"} {set from_name [get_property $from name]}
            if {$to != "NULL"} {set to_name [get_property $to name]}
            opentools_macro_record $stream ARC $from_name $to_name [sta::TimingArcSet_full_name $arc]
        }
        opentools_macro_record $stream LIMIT timing_role not_exported
        opentools_macro_record $stream LIMIT liberty_pg_associations not_exported
        write_db $database_file
        opentools_macro_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_MACRO_EXPORT_COMPLETE
}
