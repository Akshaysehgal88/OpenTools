module gold #(parameter integer WIDTH = 8)
  (input [WIDTH-1:0] events, mask, input functional_mode,
   output [WIDTH-1:0] pending, output irq);
  assign pending = events & mask;
  assign irq = |pending;
endmodule
