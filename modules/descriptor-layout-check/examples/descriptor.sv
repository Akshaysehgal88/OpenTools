module descriptor_top #(parameter ADDR_W = 64) ();
  typedef enum logic [31:0] { OP_READ = 1, OP_WRITE = 2 } opcode_t;
  typedef struct packed {
    logic [31:0] padding;
    logic [31:0] reserved;
    opcode_t opcode;
    logic [31:0] length;
    logic [ADDR_W-1:0] address;
  } descriptor_t;
endmodule
