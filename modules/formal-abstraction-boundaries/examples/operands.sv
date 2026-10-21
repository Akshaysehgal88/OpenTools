`include "selection.vh"
module top(input [1:0] source, output [1:0] left, right);
  assign left = source + 2'd1;
`ifdef BUG
  assign right = source == 2 ? 2'd1 : ((source + 2'd1) ^ 2'b11);
`else
  assign right = (source + 2'd1) ^ 2'b11;
`endif
  wire [3:0] boundary = {right, left};
`ifdef CORRELATED
  always @* assume(right == (left ^ 2'b11));
`endif
`ifdef EXACT
  always @* assume(left == (source + 2'd1));
`endif
`ifdef RESTRICTED
  always @* assume(source == 0 && left == 1);
`endif
  always @* assert(({1'b0, left} + {1'b0, right}) == 3'd3);
endmodule
