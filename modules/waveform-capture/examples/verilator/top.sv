`timescale 1ns/1ns
module arbiter(
    input logic clk, reset_n, config_write, config_value,
    output logic grant, quiesce_active
);
    always_ff @(posedge clk) begin
        if (!reset_n) quiesce_active <= 0;
        else if (config_write) quiesce_active <= config_value;
    end
    assign grant = reset_n && !quiesce_active;
endmodule

module dma_engine(
    input logic clk, reset_n, request_valid, grant,
    output logic request_ready, accepted, outstanding, response, timeout,
    output logic [5:0] age
);
    assign request_ready = reset_n && !outstanding;
    always_ff @(posedge clk) begin
        if (!reset_n) begin
            accepted <= 0; outstanding <= 0; response <= 0; timeout <= 0; age <= 0;
        end else begin
            accepted <= 0; response <= 0;
            if (request_valid && request_ready) begin
                accepted <= 1; outstanding <= 1; age <= 0;
            end else if (outstanding) begin
                if (grant) begin response <= 1; outstanding <= 0; end
                else if (age == 29) timeout <= 1;
                else age <= age + 1;
            end
        end
    end
endmodule

module top(
    input logic clk, reset_n, request_valid, config_write, config_value,
    output logic request_ready, accepted, outstanding, response, timeout,
    output logic grant, quiesce_active,
    output logic [5:0] age
);
    arbiter fabric(.clk(clk),.reset_n(reset_n),.config_write(config_write),.config_value(config_value),
                   .grant(grant),.quiesce_active(quiesce_active));
    dma_engine dma(.clk(clk),.reset_n(reset_n),.request_valid(request_valid),.grant(grant),
                   .request_ready(request_ready),.accepted(accepted),.outstanding(outstanding),
                   .response(response),.timeout(timeout),.age(age));
    logic [31:0] unrelated_activity;
    always_ff @(posedge clk) begin
        if (!reset_n) unrelated_activity <= 0;
        else unrelated_activity <= unrelated_activity + 32'h1234567;
    end
endmodule
