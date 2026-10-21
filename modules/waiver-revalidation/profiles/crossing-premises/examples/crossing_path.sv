module crossing_path(input logic source_clk,destination_clk,source_reset,destination_reset,
    destination_enable,update_cfg,output logic [3:0] source_cfg=3,destination_cfg=0,
    output logic source_ready=0,output wire destination_active);
    assign destination_active=destination_enable && !destination_reset;
    always @(posedge source_clk or posedge source_reset)
        if(source_reset)begin source_cfg<=3;source_ready<=0;end
        else begin source_ready<=1;if(update_cfg)source_cfg<=7;end
    always @(posedge destination_clk or posedge destination_reset)
        if(destination_reset)destination_cfg<=0;
        else if(destination_active)destination_cfg<=source_cfg;
endmodule

module crossing_top;
    logic source_clk=0,destination_clk=0,source_reset=0,destination_reset=0,window=0;
    logic [3:0] destination_enable=0,update_cfg=0;
    wire [3:0] source_cfg[4],destination_cfg[4];
    wire [3:0] source_ready,destination_active;
    for(genvar i=0;i<4;i++)begin:cases
        crossing_path dut(.source_clk(source_clk),.destination_clk(destination_clk),.source_reset(source_reset),.destination_reset(destination_reset),
            .destination_enable(destination_enable[i]),.update_cfg(update_cfg[i]),.source_cfg(source_cfg[i]),.destination_cfg(destination_cfg[i]),
            .source_ready(source_ready[i]),.destination_active(destination_active[i]));
        initial $display("CONFIG %0d %0d %0d",i,i==1,i==3);
    end
    task automatic tick_source;
        #1;source_clk=1;#1;source_clk=0;#1;
    endtask
    task automatic tick_destination;
        #1;destination_clk=1;#1;destination_clk=0;#1;
    endtask
    task automatic observe(input int seq,input bit sampled);
        for(int i=0;i<4;i++)
            $display("CROSSING %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d",i,seq,$time,source_cfg[i],window,source_reset,destination_active[i],source_ready[i],sampled,destination_cfg[i]);
    endtask
    initial begin
        #1;source_reset=1;destination_reset=1;tick_source();tick_destination();observe(0,0);
        source_reset=0;destination_reset=0;destination_enable[3]=1;#1;observe(1,0);
        tick_source();observe(2,0);
        destination_enable='1;window=1;#1;observe(3,0);
        tick_destination();observe(4,1);
        update_cfg[1]=1;tick_source();update_cfg=0;observe(5,0);
        tick_destination();observe(6,1);
        window=0;#1;observe(7,0);$finish;
    end
endmodule
