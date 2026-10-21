# Final native clock collections. Definition targets and timing reference differ.
proc opentools_clock_string {value} {
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
proc opentools_clock_record {stream args} {
    set fields {};foreach value $args {lappend fields [opentools_clock_string $value]}
    puts $stream "\[[join $fields ,]\]"
}
proc opentools_export_clocks {run_ref case_ports endpoint output_file database_file} {
    if {[file exists $output_file] || [file exists $database_file]} {error "Choose new output paths"}
    if {[llength [get_pins $endpoint]] != 1} {error "Select one native timing endpoint"}
    sta::update_generated_clks
    set stream [open $output_file {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_clock_record $stream HEADER opentools.sta-lineage-native.v1 $run_ref $endpoint
        if {[namespace exists ::opentools_sta]} {
            opentools_clock_record $stream TRACE $::opentools_sta::initialized $::opentools_sta::active $::opentools_sta::ended $::opentools_sta::initial_count
            set index 0
            foreach event $::opentools_sta::events {
                set current [get_clocks [dict get $event name]]
                set bound [expr {$current eq [dict get $event clock_object]}]
                opentools_clock_record $stream GENERATED $index [dict get $event name] [dict get $event master] [dict get $event reference] [dict get $event divide] [dict get $event multiply] [dict get $event duty] [dict get $event invert] [dict get $event combinational] [dict get $event add] $bound [dict get $event edges] [dict get $event shifts] {*}[dict get $event targets]
                incr index
            }
        } else {opentools_clock_record $stream TRACE 0 0 0 -1}
        foreach clock [all_clocks] {
            set name [get_full_name $clock]
            opentools_clock_record $stream CLOCK $name [get_property $clock period] [get_property $clock is_generated] [get_property $clock is_propagated] [sta::Clock_waveform_valid $clock]
            set waveform {};foreach edge [sta::Clock_waveform $clock] {lappend waveform [sta::format_time $edge 6]}
            opentools_clock_record $stream WAVEFORM $name {*}$waveform
            foreach pin [get_property $clock sources] {opentools_clock_record $stream TARGET $name [get_full_name $pin]}
            foreach pin [all_registers -clock $clock -clock_pins] {opentools_clock_record $stream COVERAGE $name [get_full_name $pin]}
        }
        foreach pin [all_registers -clock_pins] {opentools_clock_record $stream REGISTER_PIN [get_full_name $pin]}
        foreach port $case_ports {
            set pin [get_ports $port]
            if {[llength $pin] != 1} {error "Case port missing/ambiguous"}
            opentools_clock_record $stream CASE $port [sta::pin_case_logic_value [sta::get_port_pin $pin]]
        }
        set paths [find_timing_paths -to [get_pins $endpoint] -path_delay max -group_count 20]
        opentools_clock_record $stream PATH_COUNT [llength $paths]
        foreach path $paths {opentools_clock_record $stream PATH [get_property $path slack] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]]}
        write_db $database_file
        opentools_clock_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_STA_LINEAGE_EXPORT_COMPLETE
}
