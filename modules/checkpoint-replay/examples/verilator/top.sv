// Clocked read-before-write memory with a one-transaction output pipeline.
module top(
    input logic clk,
    input logic reset_n,
    input logic [3:0] addr,
    input logic [7:0] data_in,
    input logic write_enable,
    input logic [3:0] probe_addr,
    output logic [7:0] probe_data,
    output logic [7:0] data_out,
    output logic valid
);
    logic [7:0] memory [0:15];
    logic [7:0] read_stage;
    logic stage_valid;
    assign probe_data = memory[probe_addr];
    always_ff @(posedge clk) begin
        if (!reset_n) begin
            for (int i = 0; i < 16; i++) memory[i] <= 0;
            read_stage <= 0;
            data_out <= 0;
            stage_valid <= 0;
            valid <= 0;
        end else begin
            read_stage <= memory[addr];
            data_out <= read_stage;
            stage_valid <= 1;
            valid <= stage_valid;
            if (write_enable) memory[addr] <= data_in;
        end
    end
endmodule
