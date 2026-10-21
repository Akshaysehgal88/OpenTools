`include "selection.vh"
`define HOLD_STREAM(valid, ready, data) (!$past(valid && !ready) || (valid && data == $past(data)))

// Forwarding adapter; its stability claim needs a producer-side contract.
module consumer(input clk);
  (* anyseq *) reg valid, ready;
  (* anyseq *) reg [1:0] data;
  reg [1:0] age = 0;
  wire reset = age == 0;
  wire out_valid = valid;
  wire [1:0] out_data = data;
  always @(posedge clk) begin
    if (age != 3) age <= age + 1;
    if (!reset) begin
`ifdef EXCLUDED
      assume(ready);
`elsif HELD
      if (age >= 2) assume(`HOLD_STREAM(valid, ready, data));
`endif
      cover(valid && !ready);
    end
    if (age >= 2) assert(`HOLD_STREAM(out_valid, ready, out_data));
  end
endmodule

module producer(input clk);
  (* anyseq *) reg incoming, ready;
  (* anyseq *) reg [1:0] incoming_data;
  reg [1:0] age = 0;
  wire reset = age == 0;
  reg valid = 0;
  reg [1:0] data = 0;
  always @(posedge clk) begin
    if (age != 3) age <= age + 1;
    if (reset) begin valid <= 0; data <= 0; end
    else if (!valid || ready) begin valid <= incoming; data <= incoming_data; end
    if (age >= 2) assert(`HOLD_STREAM(valid, ready, data));
  end
endmodule
