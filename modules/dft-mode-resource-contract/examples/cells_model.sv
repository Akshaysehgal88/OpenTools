// Owned ideal functional model. No characterized timing or physical power claim.
module SCANR_CELL(input CK,RN,D,SI,SE,output reg Q);
  always @(posedge CK or negedge RN)
    if (!RN) Q <= 1'b0;
    else Q <= SE ? SI : D;
endmodule
