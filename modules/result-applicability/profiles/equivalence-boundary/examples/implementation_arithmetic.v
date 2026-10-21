module gate #(parameter integer MUTATION = 0)
  (input [3:0] operand_a, operand_b, input functional_mode,
   output [3:0] sum, output carry);
  wire [4:0] total = ({1'b0, operand_a} ^ {1'b0, operand_b})
                   + (({1'b0, operand_a} & {1'b0, operand_b}) << 1);
  assign sum = total[3:0] ^ ((MUTATION && functional_mode) ? 4'b0001 : 4'b0000);
  assign carry = total[4];
endmodule
