proc opentools_endpoint_string {value} {
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
proc opentools_endpoint_record {stream args} {
    set fields {};foreach v $args {lappend fields [opentools_endpoint_string $v]};puts $stream "\[[join $fields ,]\]"
}
proc opentools_endpoint_clock {path property} {
    set clock [get_property $path $property]
    if {$clock eq "NULL"} {return ""};return [get_full_name $clock]
}
proc opentools_export_endpoints {run_ref case_ports} {
    check_setup -unconstrained_endpoints -verbose > unconstrained.txt
    set stream [open native.jsonl {WRONLY CREAT EXCL}]
    fconfigure $stream -encoding utf-8 -translation lf
    try {
        opentools_endpoint_record $stream HEADER opentools.sta-endpoint-native.v1 $run_ref
        foreach clock [all_clocks] {
            set name [get_full_name $clock]
            opentools_endpoint_record $stream CLOCK $name [get_property $clock period] [get_property $clock is_propagated]
            foreach pin [get_property $clock sources] {opentools_endpoint_record $stream SOURCE $name [get_full_name $pin]}
            foreach pin [all_registers -clock $clock -clock_pins] {opentools_endpoint_record $stream COVERAGE $name [get_full_name $pin]}
        }
        foreach pin [all_registers -clock_pins] {opentools_endpoint_record $stream CLOCK_PIN [get_full_name $pin]}
        foreach port $case_ports {
            set objects [get_ports $port];if {[llength $objects]!=1} {error "Case port absent/ambiguous"}
            opentools_endpoint_record $stream CASE $port [sta::pin_case_logic_value [sta::get_port_pin $objects]]
        }
        foreach kind {output data} {
            if {$kind eq "output"} {set endpoints [all_outputs]} else {set endpoints [all_registers -data_pins]}
            foreach endpoint $endpoints {
                set name [get_full_name $endpoint]
                if {$kind eq "output"} {set pin [sta::get_port_pin $endpoint]} else {set pin $endpoint}
                set paths [find_timing_paths -to $endpoint -unconstrained -path_delay max -group_count 20]
                opentools_endpoint_record $stream ENDPOINT $name $kind [sta::pin_logic_value $pin] [sta::pin_case_logic_value $pin] [sta::pin_sim_logic_value $pin] [llength $paths]
                foreach path $paths {
                    opentools_endpoint_record $stream PATH $name [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]] [sta::PathEnd_is_unconstrained $path] [sta::PathEnd_is_output_delay $path] [sta::PathEnd_is_check $path] [get_property $path slack] [sta::format_time [sta::PathEnd_margin $path] 6] [opentools_endpoint_clock $path startpoint_clock] [opentools_endpoint_clock $path endpoint_clock]
                }
            }
        }
        write_db native.odb
        write_sdc consumed.sdc
        opentools_endpoint_record $stream END
    } finally {close $stream}
    puts OPENTOOLS_STA_ENDPOINT_RUN_COMPLETE
}
