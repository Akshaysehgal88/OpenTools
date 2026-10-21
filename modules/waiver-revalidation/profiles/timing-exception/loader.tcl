# Closed precedence scope: fresh linked design, no imported SDC, one setup false path.
source config.tcl
read_verilog design.v
read_lef cells.lef
read_liberty cells.lib
link_design top
foreach clock $clocks {lassign $clock name port period;create_clock -name $name -period $period [get_ports $port]}
foreach {port value} $phase_cases {set_case_analysis $value [get_ports $port]}
set_propagated_clock [all_clocks]
source trace_exception.tcl
source export_reach.tcl
if {$trace_enabled} {opentools_exception_trace_start}
set from_cells [get_cells $from_pattern];set to_cells [get_cells $to_pattern]
if {[llength $from_cells]<1 || [llength $to_cells]<1 || [llength $from_cells]*[llength $to_cells]>64} {error "Select 1..64 native instance pairs"}
set stream [open native.jsonl {WRONLY CREAT EXCL}]
fconfigure $stream -encoding utf-8 -translation lf
try {
    opentools_reach_record $stream HEADER opentools.sta-exception-native.v1 $run_ref
    opentools_reach_record $stream SELECTOR from {*}[opentools_exception_names $from_cells]
    opentools_reach_record $stream SELECTOR to {*}[opentools_exception_names $to_cells]
    opentools_reach_context $stream before $case_ports
    opentools_reach_query $stream before $from_cells $to_cells
    set_false_path -setup -from $from_cells -to $to_cells
    opentools_reach_context $stream after $case_ports
    opentools_reach_query $stream after $from_cells $to_cells
    if {$trace_enabled} {opentools_exception_trace_end}
    opentools_reach_events $stream
    write_db native.odb
    write_sdc consumed.sdc
    opentools_reach_record $stream END
} finally {close $stream}
puts OPENTOOLS_STA_EXCEPTION_RUN_COMPLETE
