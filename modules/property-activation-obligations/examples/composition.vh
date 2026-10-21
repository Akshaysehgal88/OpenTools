`include "selection.vh"
`include "checker.sv"
module `SUBJECT(input aon_clk, functional_clk, reset, `MODE, `EVENT, `CONDITION);
endmodule
module `DECOY(input aon_clk, functional_clk, reset, `MODE, `EVENT, `CONDITION);
endmodule

`ifndef OMIT_BIND
`ifdef BIND_DECOY
bind `DECOY activation_checker audit (
`else
bind `SUBJECT activation_checker audit (
`endif
`ifdef CHECK_GATED
  .checker_clk(functional_clk),
`else
  .checker_clk(aon_clk),
`endif
`ifdef MASK_RESET
  .reset(reset || `MODE),
`else
  .reset(reset),
`endif
  .mode(`MODE),
`ifdef BAD_GUARD
  .extra_disable(`MODE),
`else
  .extra_disable(1'b0),
`endif
  .event_req(`EVENT), .condition_ok(`CONDITION));
`endif

bind `SUBJECT obligation_observer observe (
  .observer_clk(aon_clk), .reset(reset), .mode(`MODE),
  .event_req(`EVENT), .condition_ok(`CONDITION));

module top(input aon_clk, functional_clk, reset, mode, event_req, condition_ok);
  `SUBJECT dut(.aon_clk(aon_clk), .functional_clk(functional_clk), .reset(reset),
    .`MODE(mode), .`EVENT(event_req), .`CONDITION(condition_ok));
  `DECOY decoy(.aon_clk(aon_clk), .functional_clk(functional_clk), .reset(reset),
    .`MODE(mode), .`EVENT(1'b0), .`CONDITION(1'b1));
endmodule
