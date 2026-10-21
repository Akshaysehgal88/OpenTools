proc opentools_reach_string {value} {
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
proc opentools_reach_record {stream args} {
    set fields {};foreach value $args {lappend fields [opentools_reach_string $value]};puts $stream "\[[join $fields ,]\]"
}
proc opentools_reach_query {stream phase from_cells to_cells} {
    foreach from $from_cells {
        foreach to $to_cells {
            # One maximum-setup representative per native path group; retain all.
            set paths [find_timing_paths -from $from -to $to -path_delay max -group_count 1]
            opentools_reach_record $stream PAIR $phase [get_full_name $from] [get_full_name $to] [llength $paths]
            foreach path $paths {
                opentools_reach_record $stream PATH $phase [get_full_name $from] [get_full_name $to] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]] [get_property $path slack]
            }
        }
    }
}
proc opentools_reach_context {stream phase case_ports} {
    foreach port $case_ports {
        set pin [get_ports $port];if {[llength $pin]!=1} {error "Case port missing/ambiguous"}
        opentools_reach_record $stream CASE $phase $port [sta::pin_case_logic_value [sta::get_port_pin $pin]]
    }
    foreach clock [all_clocks] {
        opentools_reach_record $stream CLOCK $phase [get_full_name $clock] [get_property $clock period]
        foreach pin [all_registers -clock $clock -clock_pins] {opentools_reach_record $stream MEMBERSHIP $phase [get_full_name $clock] [get_full_name $pin]}
    }
    foreach pin [all_registers -clock_pins] {opentools_reach_record $stream REGISTER_PIN $phase [get_full_name $pin]}
    foreach pin [all_registers -data_pins] {opentools_reach_record $stream DATA_PIN $phase [get_full_name $pin]}
    foreach pin [all_registers -output_pins] {opentools_reach_record $stream OUTPUT_PIN $phase [get_full_name $pin]}
}
proc opentools_reach_events {stream} {
    opentools_reach_record $stream TRACE $::opentools_exception::active $::opentools_exception::ended $::opentools_exception::constructors [llength $::opentools_exception::events]
    set index 0
    foreach event $::opentools_exception::events {
        opentools_reach_record $stream APPLICATION $index [dict get $event min_max] [dict get $event through_count] [dict get $event comment]
        foreach side {from to} {
            set selector [dict get $event $side]
            opentools_reach_record $stream EDGE $index $side [dict get $selector rf] [expr {$side eq "to" ? [dict get $selector end_rf] : ""}]
            foreach kind {pins clocks instances} {opentools_reach_record $stream RESOLVED $index $side $kind {*}[dict get $selector $kind]}
        }
        incr index
    }
}
