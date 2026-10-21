module ram_wrapper(input logic clk,reset,valid,input logic [1:0] operation,word_address,
    input logic [31:0] write_data,input logic [3:0] byte_enable,input logic [38:0] inject_mask,input logic force_done,
    output logic ack=0,old_read=0,correctable=0,uncorrectable=0,committed=0,error=0,
    output logic before_initialized=0,after_initialized=0,
    output logic [38:0] before_codeword=0,after_codeword=0,
    output logic [31:0] old_data=0,read_data=0,output wire init_done);
    import opentools_ecc39::*;
    logic [38:0] memory[4];
    logic [3:0] initialized=0;
    assign init_done=(&initialized) || force_done;
    // Two check-bit flips in encoded zero: controlled invalid startup, not X/power modeling.
    always @(posedge clk or posedge reset)begin:memory_access
        decoded_t decoded;
        logic [31:0] merged;
        logic [38:0] next_word;
        logic next_initialized;
        if(reset)begin
            for(int word_index=0;word_index<4;word_index++)memory[word_index]<=39'd3;
            initialized<=0;ack<=0;old_read<=0;correctable<=0;uncorrectable<=0;committed<=0;error<=0;
            before_initialized<=0;after_initialized<=0;before_codeword<=0;after_codeword<=0;old_data<=0;read_data<=0;
        end else begin
            ack<=0;old_read<=0;correctable<=0;uncorrectable<=0;committed<=0;error<=0;old_data<=0;read_data<=0;
            if(valid)begin
                ack<=1;before_codeword<=memory[word_address];before_initialized<=initialized[word_address];
                next_word=memory[word_address];next_initialized=initialized[word_address];decoded=decode(memory[word_address]);
                case(operation)
                    0:begin next_word=encode(write_data);next_initialized=1;committed<=1;end // scrub full codeword
                    1:begin old_read<=1;correctable<=decoded.correctable;uncorrectable<=decoded.uncorrectable;
                        error<=decoded.uncorrectable;old_data<=decoded.data;read_data<=decoded.data;end
                    2:begin
                        if(byte_enable==4'hf)begin next_word=encode(write_data);next_initialized=1;committed<=1;end
                        else if(byte_enable!=0)begin
                            old_read<=1;correctable<=decoded.correctable;uncorrectable<=decoded.uncorrectable;
                            error<=decoded.uncorrectable;old_data<=decoded.data;
                            if(!decoded.uncorrectable)begin
                                merged=decoded.data;
                                for(int lane=0;lane<4;lane++)if(byte_enable[lane])merged[lane*8+:8]=write_data[lane*8+:8];
                                next_word=encode(merged);committed<=1;
                            end
                        end
                    end
                    3:begin next_word=memory[word_address]^inject_mask;committed<=1;end // test-only injection, no initialization credit
                endcase
                memory[word_address]<=next_word;initialized[word_address]<=next_initialized;
                after_codeword<=next_word;after_initialized<=next_initialized;
            end
        end
    end
endmodule
