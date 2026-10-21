// Owned command-port model. No foundry macro, production fuse or MBIST coverage claim.
module memory_bank #(
 parameter int WORDS=4,PHYSICAL=WORDS+1,AW=$clog2(WORDS),PAW=$clog2(PHYSICAL),RESET_ASSERTED=1
)(input logic clk,reset,valid,input logic [7:0] cfg,input logic [3:0] operation,
 input logic [AW-1:0] word_address,input logic [PAW-1:0] physical_address,
 input logic [11:0] repair_input,input logic [31:0] write_data,input logic [3:0] byte_enable,
 input logic [38:0] raw_input,
 output logic accepted,address_valid,committed,error,internal_read,correctable,uncorrectable,
 output logic test_owner,test_done,repair_loaded,repair_active,ecc_enabled,released,
 output logic [WORDS-1:0] initialized,output logic [3:0] decoded_bad,decoded_spare,canonical_bad,canonical_spare,
 output logic [15:0] repair_epoch,output logic [11:0] loaded_payload,
 output logic [PAW-1:0] actual_physical,output logic [38:0] before_codeword,after_codeword,
 output logic [31:0] read_data,old_data,output logic [PHYSICAL-1:0] test_writes,test_reads);
 import opentools_ecc39::*;
 logic [38:0] memory[0:PHYSICAL-1];
 wire async_reset=(reset==RESET_ASSERTED);
 function automatic logic [PAW-1:0] selected(input logic [AW-1:0] word,input logic initializer);
   if(initializer) return repair_loaded && loaded_payload[11] && word==canonical_bad ? PAW'(canonical_spare) : PAW'(word);
   return repair_loaded && repair_active && word==decoded_bad ? PAW'(decoded_spare) : PAW'(word);
 endfunction
 always @(posedge clk or posedge async_reset)begin:access
   decoded_t decoded;
   logic [PAW-1:0] target;
   logic [3:0] bad,spare;
   logic format_ok;
   logic [31:0] merged;
   logic [38:0] next_word;
   if(async_reset)begin
     for(int i=0;i<PHYSICAL;i++)memory[i]<=39'd3;
     accepted<=0;address_valid<=0;committed<=0;error<=0;internal_read<=0;correctable<=0;uncorrectable<=0;
     test_owner<=1;test_done<=0;repair_loaded<=0;repair_active<=0;ecc_enabled<=0;released<=0;initialized<=0;
     decoded_bad<=0;decoded_spare<=0;canonical_bad<=0;canonical_spare<=0;repair_epoch<=0;loaded_payload<=0;
     actual_physical<=0;before_codeword<=0;after_codeword<=0;read_data<=0;old_data<=0;test_writes<=0;test_reads<=0;
   end else begin
     accepted<=0;address_valid<=0;committed<=0;error<=0;internal_read<=0;correctable<=0;uncorrectable<=0;
     actual_physical<=0;before_codeword<=0;after_codeword<=0;read_data<=0;old_data<=0;
     if(valid)begin
       if(operation==0 || operation==1)begin
         if((test_owner || cfg[5]) && physical_address<PHYSICAL)begin
           accepted<=1;address_valid<=1;actual_physical<=physical_address;before_codeword<=memory[physical_address];after_codeword<=memory[physical_address];
           if(operation==0)begin memory[physical_address]<=raw_input;after_codeword<=raw_input;committed<=1;test_writes[physical_address]<=1;end
           else begin internal_read<=1;test_reads[physical_address]<=1;end
         end
       end else if(operation==2 && test_owner)begin
         // Limited selected raw write/read exercise, not an MBIST algorithm certificate.
         accepted<=1;test_done<=($countones(test_writes & test_reads)==WORDS);
       end else if(operation==3 && test_owner)begin
         // Owned12-bit entry: valid11,bad9:6,spare4:1,reserved10/5/0.
         bad=cfg[0]?repair_input[8:5]:repair_input[9:6];spare=repair_input[4:1];
         format_ok=((repair_input & 12'h421)==0) && (!repair_input[11] || (bad<WORDS && spare>=WORDS && spare<PHYSICAL));
         accepted<=1;decoded_bad<=bad;decoded_spare<=spare;canonical_bad<=repair_input[9:6];canonical_spare<=repair_input[4:1];
         loaded_payload<=repair_input;repair_epoch<=repair_epoch+1;repair_loaded<=format_ok;repair_active<=format_ok && repair_input[11];
       end else if(operation==4 && test_owner)begin accepted<=1;ecc_enabled<=1;end
       else if(operation==10 && test_owner)begin accepted<=1;ecc_enabled<=0;end
       else if(operation==5 && test_owner && ecc_enabled && (repair_loaded || cfg[4]))begin
         target=selected(word_address,1);next_word=encode(write_data);
         if(cfg[2])next_word^=39'd3;
         accepted<=1;address_valid<=1;committed<=1;actual_physical<=target;before_codeword<=memory[target];after_codeword<=next_word;memory[target]<=next_word;initialized[word_address]<=1;
       end else if(operation==6 && test_owner)begin
         accepted<=1;
         if((test_done && repair_loaded && ecc_enabled && (&initialized)) || cfg[1])begin released<=1;test_owner<=0;end
       end else if((operation==7 || operation==8) && !test_owner && released)begin
         target=selected(word_address,0);decoded=decode(memory[target]);next_word=memory[target];
         accepted<=1;address_valid<=1;actual_physical<=target;before_codeword<=memory[target];after_codeword<=memory[target];
         if(operation==7 || byte_enable!=4'hf && byte_enable!=0)begin
           internal_read<=1;correctable<=ecc_enabled && decoded.correctable;uncorrectable<=ecc_enabled && decoded.uncorrectable;
           error<=ecc_enabled && decoded.uncorrectable;old_data<=ecc_enabled?decoded.data:memory[target][31:0];
         end
         if(operation==7)read_data<=ecc_enabled?decoded.data:memory[target][31:0];
         else if(byte_enable==4'hf)begin next_word=encode(write_data);committed<=1;initialized[word_address]<=1;end
         else if(byte_enable!=0 && !(ecc_enabled && decoded.uncorrectable))begin
           merged=ecc_enabled?decoded.data:memory[target][31:0];
           for(int lane=0;lane<4;lane++)if(byte_enable[lane])
             if(cfg[3])merged[(3-lane)*8+:8]=write_data[lane*8+:8];else merged[lane*8+:8]=write_data[lane*8+:8];
           next_word=encode(merged);committed<=1;
         end
         if(operation==8)begin memory[target]<=next_word;after_codeword<=next_word;end
       end
     end
   end
 end
endmodule
