module storage_top;
    logic clk=0,reset=0,valid=0,force_done=0,released=0;
    logic [1:0] operation=0,word_address=0;
    logic [31:0] write_data=0;
    logic [3:0] byte_enable=0;
    logic [38:0] inject_mask=0;
    wire ack,old_read,correctable,uncorrectable,committed,error,before_initialized,after_initialized,init_done;
    wire [38:0] before_codeword,after_codeword;
    wire [31:0] old_data,read_data;
    wire codec_done;
    logic memory_done=0;
    codec_probes probes(.done(codec_done));
    ram_wrapper ram(.*);
    int scenario=0,seq=0,master=0,target=0;
    task automatic tick;
        #1;clk=1;#1;clk=0;#1;
    endtask
    task automatic access(input int op,word_index,input logic [31:0] data,input logic [3:0] lanes,input logic [38:0] mask);
        operation=2'(op);word_address=2'(word_index);write_data=data;byte_enable=lanes;inject_mask=mask;valid=1;tick();
        $display("MEM %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,$time,
            master,op,word_index,data,lanes,mask,ack,old_read,correctable,uncorrectable,committed,error,before_codeword,after_codeword,
            before_initialized,after_initialized,old_data,read_data);
        $display("CONTROL %0d %0d %0d %0d",scenario,seq,init_done,released);
        seq++;valid=0;
    endtask
    task automatic release_master;
        released=1;#1;$display("RELEASE %0d %0d %0t %0d %0d %0d",scenario,seq,$time,master,target,init_done);seq++;
    endtask
    initial begin
        for(int case_index=0;case_index<9;case_index++)begin
            scenario=case_index;seq=0;released=0;force_done=0;valid=0;
            master=(case_index==3||case_index==4||case_index==5||case_index==8)?1:0;target=(master==1)?2:0;
            $display("CONFIG %0d %0d %0d",scenario,master,target);
            reset=1;tick();reset=0;
            for(int w=0;w<4;w++)$display("INITIAL %0d %0d %0t %0d %0d",scenario,w,$time,ram.memory[w],ram.initialized[w]);
            if(case_index==1||case_index==4||case_index==6||case_index==7)begin
                for(int w=0;w<4;w++)begin master=2;access(0,w,32'd0,4'hf,39'd0);end
                master=(case_index==4)?1:0;
            end
            if(case_index==2)access(2,target,32'h11223344,4'hf,39'd0);
            if(case_index==5)begin master=2;access(0,0,32'd0,4'hf,39'd0);master=1;force_done=1;end
            if(case_index==6)begin master=3;access(3,target,32'd0,4'd0,39'd4);master=0;end
            if(case_index==7)begin master=3;access(3,target,32'd0,4'd0,39'd20);master=0;end
            if(case_index==8)begin master=3;access(3,target,32'd0,4'd0,39'd3);master=1;end // valid zero code, still no admitted initializer
            release_master();
            access(2,target,32'haabbccdd,(case_index==6)?4'h2:4'h1,39'd0);
            access(1,target,32'd0,4'd0,39'd0);
        end
        memory_done=1;
    end
    initial begin wait(codec_done && memory_done);#1;$finish;end
endmodule
