`include "selection.vh"
`define HOLD_REQUEST(req, ack) (!$past(req && !ack) || req)

// Owned synchronous logical model: a pulse can wake the block before it can ack.
module consumer(input clk);
  (* anyseq *) reg request, sleep_cmd, external_resume;
  reg [1:0] age = 0;
  wire reset = age == 0;
  reg asleep = 1, ack = 0;
  always @(posedge clk) begin
    if (age != 3) age <= age + 1;
    if (reset) begin asleep <= 1; ack <= 0; end
    else begin
      ack <= request && !asleep;
      if (request || external_resume) asleep <= 0;
      else if (sleep_cmd) asleep <= 1;
    end
    if (!reset) begin
`ifdef EXCLUDED
      assume(!request || !asleep);
`elsif HELD
      if (age >= 2) assume(`HOLD_REQUEST(request, ack));
`endif
      cover(request && asleep);
    end
    if (age == 3 && $past(request, 2)) assert(ack || $past(ack));
  end
endmodule

// A separate producer. Its hold guarantee is asserted, never assumed.
module producer(input clk);
  (* anyseq *) reg incoming, ack;
  reg [1:0] age = 0;
  wire reset = age == 0;
  reg request = 0;
  always @(posedge clk) begin
    if (age != 3) age <= age + 1;
    if (reset) request <= 0;
    else if (!request || ack) request <= incoming;
    if (age >= 2) assert(`HOLD_REQUEST(request, ack));
  end
endmodule
