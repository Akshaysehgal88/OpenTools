module top(input clk, reset, functional_mode, fault, req_valid, rsp_ready,
           input [7:0] req_id, input [15:0] req_data,
           output req_ready, rsp_valid, output [7:0] rsp_id, output [15:0] rsp_data);
  reg busy;
  reg [7:0] saved_id;
  reg [15:0] saved_data;
  assign req_ready = !busy;
  assign rsp_valid = busy;
  assign rsp_id = saved_id;
  assign rsp_data = saved_data ^ ((fault && functional_mode) ? 16'h0001 : 16'h0000);
  always @(posedge clk) begin
    if (reset) begin busy <= 0; saved_id <= 0; saved_data <= 0; end
    else begin
      if (rsp_valid && rsp_ready) busy <= 0;
      if (req_valid && req_ready) begin busy <= 1; saved_id <= req_id; saved_data <= req_data ^ 16'h005a; end
    end
  end
endmodule
