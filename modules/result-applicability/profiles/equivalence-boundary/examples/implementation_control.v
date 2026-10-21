module gate #(parameter integer WIDTH = 8, parameter integer MUTATION = 0)
  (input [WIDTH-1:0] events, mask, input functional_mode,
   output [WIDTH-1:0] pending, output irq);
  wire [WIDTH-1:0] selected = ~(~events | ~mask);
  assign pending = selected ^ ((MUTATION && functional_mode) ? {1'b1, {(WIDTH-1){1'b0}}} : {WIDTH{1'b0}});
  assign irq = |pending;
endmodule
