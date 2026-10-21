module configuration_top #(parameter int WORD_BITS=32, DEPTH=16, FEATURE=1, MODE=0) ();
    logic [WORD_BITS-1:0] storage [DEPTH];
    // Byte-rounded capture carrier; WORD_BITS remains the independent logical value.
    typedef struct packed { logic [((WORD_BITS+7)/8)*8-1:0] payload; } configuration_t;
endmodule
