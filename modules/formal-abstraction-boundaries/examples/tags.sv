`include "selection.vh"
// A combinational tag correspondence, not a complete transaction protocol.
module top(input [1:0] source, output [1:0] left, right);
  assign left = source + 2'd1;
`ifdef BUG
  assign right = source == 2 ? 2'd0 : (source + 2'd1);
`else
  assign right = source + 2'd1;
`endif
  wire [3:0] boundary = {right, left};
`ifdef CORRELATED
  always @* assume(right == left);
`endif
`ifdef EXACT
  always @* assume(left == (source + 2'd1));
`endif
`ifdef RESTRICTED
  always @* assume(source == 0 && left == 1);
`endif
  always @* assert(left == right);
endmodule
