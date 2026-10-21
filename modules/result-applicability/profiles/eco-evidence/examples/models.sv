// Owned primitive model profile. No electrical, route or whole-design equivalence claim.
module ECO_AND(input A,B,output Y);assign Y=A&B;endmodule
module ECO_OR(input A,B,output Y);assign Y=A|B;endmodule
module ECO_INV(input A,output Y);assign Y=~A;endmodule
module ECO_BUF(input A,output Y);assign Y=A;endmodule
module ECO_DFF(input CK,RN,D,output logic Q);
 always_ff @(posedge CK or negedge RN)if(!RN)Q<=0;else Q<=D;
endmodule
