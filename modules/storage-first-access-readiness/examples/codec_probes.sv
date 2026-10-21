module codec_probes(output logic done=0);
    import opentools_ecc39::*;
    logic [31:0] reference_data=0;
    logic [38:0] reference_word=0;
`ifdef OPENTOOLS_ECC_REFERENCE
    wire [38:0] reference_encoded;
    wire [31:0] reference_decoded;
    wire [6:0] reference_syndrome;
    wire [1:0] reference_error;
    prim_secded_hamming_39_32_enc ref_enc(.data_i(reference_data),.data_o(reference_encoded));
    prim_secded_hamming_39_32_dec ref_dec(.data_i(reference_word),.data_o(reference_decoded),.syndrome_o(reference_syndrome),.err_o(reference_error));
`endif
    int probes=0;
    task automatic probe(input logic [31:0] data,input logic [38:0] fault);
        logic [38:0] word;
        decoded_t decoded;
        word=encode(data)^fault;decoded=decode(word);
        reference_data=data;reference_word=systematic(word);#1;
        if($countones(fault)==0 && (decoded.data!=data || decoded.correctable || decoded.uncorrectable))$fatal(1,"Clean code failure");
        if($countones(fault)==1 && (decoded.data!=data || !decoded.correctable || decoded.uncorrectable))$fatal(1,"Single-bit correction failure");
        if($countones(fault)==2 && (decoded.correctable || !decoded.uncorrectable))$fatal(1,"Double-bit detection failure");
`ifdef OPENTOOLS_ECC_REFERENCE
        if(systematic(encode(data))!==reference_encoded || decoded.data!==reference_decoded ||
           {decoded.overall_odd,decoded.syndrome}!==reference_syndrome ||
           {decoded.uncorrectable,decoded.correctable}!==reference_error)$fatal(1,"Pinned reference mismatch");
`endif
        $display("CODEC %0d %0d %0d %0d %0d %0d %0d %0d %0d",probes,data,fault,word,decoded.data,decoded.correctable,decoded.uncorrectable,decoded.syndrome,decoded.overall_odd);
        probes++;
    endtask
    logic [31:0] vectors[3]='{32'h00000000,32'hffffffff,32'ha5a5f00d};
    initial begin
        for(int i=0;i<3;i++)begin
            probe(vectors[i],39'd0);
            for(int a=0;a<39;a++)probe(vectors[i],39'd1<<a);
            for(int a=0;a<39;a++)for(int b=a+1;b<39;b++)probe(vectors[i],(39'd1<<a)|(39'd1<<b));
        end
        for(int bit_index=0;bit_index<32;bit_index++)probe(32'd1<<bit_index,39'd0);
        $display("CODEC_DONE %0d",probes);done=1;
    end
endmodule
