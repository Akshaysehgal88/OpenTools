module top(input clk, por, core_reset, warm, set_irq, irq_ack,
           input drop_on_hold, ack_wins, output reg pending, output irq_out);
  assign irq_out = pending && !core_reset;
  always @(posedge clk) begin
    if (por) pending <= 0;
    else if (core_reset && (!warm || drop_on_hold)) pending <= 0;
    else if (ack_wins && irq_ack && !core_reset) pending <= 0;
    else if (set_irq) pending <= 1;
    else if (irq_ack && !core_reset) pending <= 0;
  end
endmodule
