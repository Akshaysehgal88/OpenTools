module top(input clock, rst_n, retained_mode, inject_error, submit, retire,
           input [7:0] tag, input [15:0] message,
           output grant, response_valid, output [7:0] response_tag, output [15:0] response);
  reg occupied;
  reg [7:0] held_tag;
  reg [15:0] held_message;
  assign grant = !occupied;
  assign response_valid = occupied;
  assign response_tag = held_tag;
  assign response = held_message ^ ((inject_error && retained_mode) ? 16'h0001 : 16'h0000);
  always @(posedge clock) begin
    if (!rst_n) begin occupied <= 0; held_tag <= 0; held_message <= 0; end
    else begin
      if (response_valid && retire) occupied <= 0;
      if (submit && grant) begin occupied <= 1; held_tag <= tag; held_message <= message ^ 16'h00a5; end
    end
  end
endmodule
