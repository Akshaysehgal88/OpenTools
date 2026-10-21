# Pinned native constructor boundary: capture resolved objects after native success.
namespace eval ::opentools_sta {
    variable initialized 0
    variable active 0
    variable ended 0
    variable initial_count -1
    variable events {}
}
proc opentools_clock_trace_start {} {
    namespace eval ::opentools_sta {variable initialized;variable active;variable ended;variable initial_count;variable events}
    if {$::opentools_sta::initialized || [llength [info commands ::sta::opentools_original_make_generated_clock]]} {error "Clock trace already initialized"}
    set ::opentools_sta::initial_count [llength [all_clocks]]
    if {$::opentools_sta::initial_count != 0} {error "Start tracing before clock definitions"}
    set ::opentools_sta::initialized 1;set ::opentools_sta::active 1
    rename ::sta::make_generated_clock ::sta::opentools_original_make_generated_clock
    proc ::sta::make_generated_clock {name pins add source master divide multiply duty invert combinational edges shifts comment} {
        set result [::sta::opentools_original_make_generated_clock $name $pins $add $source $master $divide $multiply $duty $invert $combinational $edges $shifts $comment]
        set targets {};foreach pin $pins {lappend targets [get_full_name $pin]}
        set master_name ""
        if {$master != "NULL"} {set master_name [get_full_name $master]}
        lappend ::opentools_sta::events [dict create name $name targets $targets reference [get_full_name $source] master $master_name divide $divide multiply $multiply duty $duty invert $invert combinational $combinational add $add edges $edges shifts $shifts clock_object [get_clocks $name]]
        return $result
    }
}
proc opentools_clock_trace_end {} {
    if {!$::opentools_sta::active} {error "Clock trace is not active"}
    rename ::sta::make_generated_clock {}
    rename ::sta::opentools_original_make_generated_clock ::sta::make_generated_clock
    set ::opentools_sta::active 0;set ::opentools_sta::ended 1
}
