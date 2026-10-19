module top(
    input logic clk, reset_n, alternate,
    input logic [7:0] data,
    output logic [7:0] dma_value, fabric_value, integrated_value,
    output logic [15:0] alive
);
    import shared_pkg::*;
    import glue_pkg::*;
    localparam logic [7:0] DMA_BIAS = 8'd0;
    // Deliberate fixture defect: alternate mode violates the same DMA contract.
    assign dma_value = reset_n ? data + DMA_BIAS + {7'b0, alternate} : 8'd0;
    assign fabric_value = reset_n ? adjust(data + STEP) : 8'd0;
    assign integrated_value = dma_value ^ fabric_value;
    always_ff @(posedge clk) begin
        if (!reset_n) alive <= 0;
        else alive <= alive + 1'b1;
    end
endmodule
