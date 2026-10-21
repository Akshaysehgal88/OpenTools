module access_tb;
    logic clk=0, rst=0, req=0, is_wr=0;
    logic [2:0] addr=0;
    logic [31:0] wr_data=0, wr_biten=0;
    wire rd_ack,rd_err,wr_ack,wr_err,stall_wr,stall_rd;
    wire [31:0] rd_data;
    effects_pkg::effects__in_t hwif_in;
    effects_pkg::effects__out_t hwif_out;
    effects dut(.clk(clk),.rst(rst),.s_cpuif_req(req),.s_cpuif_req_is_wr(is_wr),
        .s_cpuif_addr(addr),.s_cpuif_wr_data(wr_data),.s_cpuif_wr_biten(wr_biten),
        .s_cpuif_rd_ack(rd_ack),.s_cpuif_rd_err(rd_err),.s_cpuif_rd_data(rd_data),
        .s_cpuif_wr_ack(wr_ack),.s_cpuif_wr_err(wr_err),
        .s_cpuif_req_stall_wr(stall_wr),.s_cpuif_req_stall_rd(stall_rd),
        .hwif_in(hwif_in),.hwif_out(hwif_out));

    task automatic tick;
        #1;clk=1;#1;clk=0;#1;
    endtask
    task automatic prime;
        req=0;
        hwif_in.pending.causes.next=0;hwif_in.pending.causes.we=0;
        hwif_in.diagnostic.causes.next=0;hwif_in.diagnostic.causes.we=0;
        rst=1;tick();rst=0;
        hwif_in.pending.causes.next=3;hwif_in.pending.causes.we=1;
        hwif_in.diagnostic.causes.next=3;hwif_in.diagnostic.causes.we=1;
        tick();hwif_in.pending.causes.we=0;hwif_in.diagnostic.causes.we=0;#1;
    endtask
    task automatic access(input int scenario,seq,input bit write_access,
        input bit diagnostic,input int data,be,output int sampled);
        int before_value,after_value,accepted,error_value;
        req=1;is_wr=write_access;addr=diagnostic?4:0;wr_data=data;
        for(int lane=0;lane<4;lane++)wr_biten[8*lane+:8]=be[lane]?8'hff:8'h00;
        #1;
        before_value=diagnostic?hwif_out.diagnostic.causes.value:hwif_out.pending.causes.value;
        sampled=rd_data;
        accepted=write_access?(wr_ack&&!stall_wr):(rd_ack&&!stall_rd);
        error_value=write_access?wr_err:rd_err;
        tick();
        after_value=diagnostic?hwif_out.diagnostic.causes.value:hwif_out.pending.causes.value;
        $display("ACCESS %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,write_access,diagnostic,before_value,after_value,sampled,data,be,wr_biten,accepted,error_value,rst,hwif_in.pending.causes.we|hwif_in.diagnostic.causes.we);
        req=0;#1;
    endtask
    int value;
    initial begin
        prime();access(0,1,0,0,0,0,value);access(0,2,1,0,value|1,1,value);
        prime();access(1,1,1,0,1,1,value);
        prime();access(2,1,1,0,1,2,value);
        prime();access(3,1,0,1,0,0,value);
        prime();access(4,1,0,1,0,0,value);
        $finish;
    end
endmodule
