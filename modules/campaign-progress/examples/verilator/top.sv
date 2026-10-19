module top(
    input logic clk, reset_n, valid, active, config_bit,
    input logic [1:0] payload,
    output logic ready,
    output logic [31:0] accepted_count,
    output logic [1:0] echo
);
    assign ready = reset_n && active;
    always_ff @(posedge clk) begin
        if (!reset_n) begin accepted_count <= 0; echo <= 0; end
        else if (valid && ready) begin
            accepted_count <= accepted_count + 1'b1;
            echo <= payload ^ {1'b0, config_bit};
        end
    end
endmodule
