module cache_handoff(input logic clk,reset,valid,payload_coherent,input logic [3:0] operation,
    input logic line_address,input logic [31:0] write_data,
    output logic [31:0] cache_a=17,cache_b=34,memory_a=17,memory_b=34,pending_data=0,read_data=0,
    output logic [7:0] cache_epoch_a=0,cache_epoch_b=0,memory_epoch_a=0,memory_epoch_b=0,pending_epoch=0,order_epoch=0,read_epoch=0,
    output logic dirty_a=0,dirty_b=0,pending=0,pending_line=0,order_seen=0,published=0,completed=0,
    output logic owner_consumer=0,clean_done=0,read_valid=0,read_control=0);
    // Two independent scalar cache lines; no eviction, autonomous completion or hidden coherence.
    // Producer stores always enter its write-back cache. Payload coherence is a separate read path.
    always @(posedge clk or posedge reset)begin
        if(reset)begin
            cache_a<=17;cache_b<=34;memory_a<=17;memory_b<=34;pending_data<=0;read_data<=0;
            cache_epoch_a<=0;cache_epoch_b<=0;memory_epoch_a<=0;memory_epoch_b<=0;pending_epoch<=0;order_epoch<=0;read_epoch<=0;
            dirty_a<=0;dirty_b<=0;pending<=0;pending_line<=0;order_seen<=0;published<=0;completed<=0;owner_consumer<=0;
            clean_done<=0;read_valid<=0;read_control<=0;
        end else begin
            clean_done<=0;read_valid<=0;read_control<=0;read_data<=0;read_epoch<=0;
            if(valid)case(operation)
                1:if(!line_address)begin cache_a<=write_data;cache_epoch_a<=cache_epoch_a+1;dirty_a<=1;end
                  else begin cache_b<=write_data;cache_epoch_b<=cache_epoch_b+1;dirty_b<=1;end
                2:begin // clean issue captures a version; issuing is not completion
                    pending<=1;pending_line<=line_address;
                    pending_data<=line_address?cache_b:cache_a;pending_epoch<=line_address?cache_epoch_b:cache_epoch_a;
                end
                3:if(pending)begin
                    if(!pending_line)begin memory_a<=pending_data;memory_epoch_a<=pending_epoch;
                        if(cache_epoch_a==pending_epoch)dirty_a<=0;end
                    else begin memory_b<=pending_data;memory_epoch_b<=pending_epoch;
                        if(cache_epoch_b==pending_epoch)dirty_b<=0;end
                    pending<=0;clean_done<=1;
                end
                4:begin published<=1;owner_consumer<=1;end // coherent control, independent of payload path
                5:begin order_seen<=1;order_epoch<=cache_epoch_a;end // ordering marker does not clean/drain
                6:begin
                    read_control<=published;read_valid<=published;
                    if(published)begin
                        read_data<=payload_coherent?(line_address?cache_b:cache_a):(line_address?memory_b:memory_a);
                        read_epoch<=payload_coherent?(line_address?cache_epoch_b:cache_epoch_a):(line_address?memory_epoch_b:memory_epoch_a);
                    end
                end
                7:completed<=1; // signal can be asserted early; review its consumed meaning
                8:owner_consumer<=0; // software reclaim can be premature; hardware does not prohibit it
                default:begin end
            endcase
        end
    end
endmodule

module handoff_top;
    logic clk=0,reset=0,valid=0,payload_coherent=0,line_address=0;
    logic [3:0] operation=0;logic [31:0] write_data=0;
    wire [31:0] cache_a,cache_b,memory_a,memory_b,pending_data,read_data;
    wire [7:0] cache_epoch_a,cache_epoch_b,memory_epoch_a,memory_epoch_b,pending_epoch,order_epoch,read_epoch;
    wire dirty_a,dirty_b,pending,pending_line,order_seen,published,completed,owner_consumer,clean_done,read_valid,read_control;
    cache_handoff storage(.*);
    int scenario,seq;
    task automatic tick;#1;clk=1;#1;clk=0;#1;endtask
    task automatic observe;
        $display("HANDOFF %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,$time,
            operation,line_address,write_data,cache_a,cache_b,memory_a,memory_b,pending_data,read_data,
            cache_epoch_a,cache_epoch_b,memory_epoch_a,memory_epoch_b,pending_epoch,order_epoch,read_epoch,
            dirty_a,dirty_b,pending,pending_line,order_seen,published,completed,owner_consumer,clean_done,read_valid,read_control);
        seq++;
    endtask
    task automatic access(input int op,line_index,input logic [31:0] data);
        operation=4'(op);line_address=1'(line_index);write_data=data;valid=1;tick();observe();valid=0;
    endtask
    initial begin
        for(int c=0;c<11;c++)begin
            scenario=c;seq=0;valid=0;operation=0;line_address=0;write_data=0;
            payload_coherent=(c==2||c==7||c==9||c==10);
            $display("CONFIG %0d %0d",scenario,payload_coherent);
            reset=1;tick();reset=0;observe();
            access(1,0,32'd165);
            if(c==1||c==3||c==4||c==5||c==6)begin
                access(2,c==4?1:0,32'd0);
                if(c!=3)access(3,0,32'd0);
            end
            if(c!=9)access(5,0,32'd0);
            access(4,0,32'd0);
            if(c==5)access(1,0,32'd60);
            if(c==6)begin access(7,0,32'd0);access(8,0,32'd0);access(1,0,32'd60);end
            access(6,c==10?1:0,32'd0);
            if(c==3)access(3,0,32'd0);
            if(c!=6)begin access(7,0,32'd0);access(8,0,32'd0);access(1,0,32'd60);end
        end
        $finish;
    end
endmodule
