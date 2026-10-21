module gold(input [3:0] operand_a, operand_b, input functional_mode,
            output [3:0] sum, output carry);
  wire [4:0] total = {1'b0, operand_a} + {1'b0, operand_b};
  assign sum = total[3:0];
  assign carry = total[4];
endmodule
