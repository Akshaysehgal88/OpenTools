module top(input clock, init_n, asleep, retain, flush_done, completion_ack,
           input inject_drop, inject_ack_priority, output reg completion_pending, output wake_out);
  assign wake_out = completion_pending && !asleep;
  always @(posedge clock) begin
    if (!init_n) completion_pending <= 0;
    else if (asleep && (!retain || inject_drop)) completion_pending <= 0;
    else if (inject_ack_priority && completion_ack && !asleep) completion_pending <= 0;
    else if (flush_done) completion_pending <= 1;
    else if (completion_ack && !asleep) completion_pending <= 0;
  end
endmodule
