# Resolved native objects, copied only when the false path is actually applied.
namespace eval ::opentools_exception {variable from_map {};variable to_map {};variable events {};variable active 0;variable ended 0;variable constructors 0}
proc opentools_exception_names {objects} {
    set out {};foreach object $objects {lappend out [get_full_name $object]};return [lsort $out]
}
proc opentools_exception_trace_start {} {
    if {$::opentools_exception::active || $::opentools_exception::ended} {error "Trace already initialized"}
    foreach method {make_exception_from make_exception_to make_false_path} {
        if {[llength [info commands ::sta::opentools_original_$method]]} {error "Native command already wrapped"}
        rename ::sta::$method ::sta::opentools_original_$method
    }
    proc ::sta::make_exception_from {pins clocks instances rf} {
        set result [::sta::opentools_original_make_exception_from $pins $clocks $instances $rf]
        dict set ::opentools_exception::from_map $result [dict create pins [opentools_exception_names $pins] clocks [opentools_exception_names $clocks] instances [opentools_exception_names $instances] rf $rf]
        incr ::opentools_exception::constructors
        return $result
    }
    proc ::sta::make_exception_to {pins clocks instances rf end_rf} {
        set result [::sta::opentools_original_make_exception_to $pins $clocks $instances $rf $end_rf]
        dict set ::opentools_exception::to_map $result [dict create pins [opentools_exception_names $pins] clocks [opentools_exception_names $clocks] instances [opentools_exception_names $instances] rf $rf end_rf $end_rf]
        incr ::opentools_exception::constructors
        return $result
    }
    proc ::sta::make_false_path {from thrus to min_max comment} {
        set result [::sta::opentools_original_make_false_path $from $thrus $to $min_max $comment]
        # Query constructors can reuse freed addresses. Freeze application values now.
        set f [dict get $::opentools_exception::from_map $from]
        set t [dict get $::opentools_exception::to_map $to]
        lappend ::opentools_exception::events [dict create from $f to $t through_count [llength $thrus] min_max $min_max comment $comment]
        return $result
    }
    set ::opentools_exception::active 1
}
proc opentools_exception_trace_end {} {
    if {!$::opentools_exception::active} {error "Trace not active"}
    foreach method {make_exception_from make_exception_to make_false_path} {
        rename ::sta::$method {}
        rename ::sta::opentools_original_$method ::sta::$method
    }
    set ::opentools_exception::active 0;set ::opentools_exception::ended 1
}
