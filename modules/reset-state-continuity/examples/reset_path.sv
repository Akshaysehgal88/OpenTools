module reset_path #(parameter bit EVENT_PROFILE=0, ALLOW_REPLAY=0)(
    input logic clk,producer_reset,consumer_reset,issue,deliver,
    output logic producer_pending=0,consumer_context=0,orphan=0,replay=0,
    output logic [3:0] producer_id=0,consumer_id=0);
    always @(posedge clk or posedge producer_reset)
        if(producer_reset)begin producer_pending<=0;producer_id<=0;end
        else if(issue)begin producer_pending<=1;producer_id<=5;end
        else if(deliver && producer_pending)producer_pending<=0;
    always @(posedge clk or posedge consumer_reset)
        if(consumer_reset)begin consumer_context<=0;consumer_id<=0;orphan<=0;replay<=0;end
        else if(issue)begin consumer_context<=1;consumer_id<=5;end
        else if(deliver && producer_pending)begin
            if(consumer_context && consumer_id==producer_id)consumer_context<=0;
            else if(EVENT_PROFILE && ALLOW_REPLAY)replay<=1;
            else orphan<=1;
        end
endmodule

module reset_top;
    logic clk=0,global_reset=0,event_reset=0,issue=0,deliver_all=0,drain=0;
    logic clock_available=1;
    integer root_edges=0;
    always @(posedge clk)root_edges=root_edges+1;
    wire [4:0] producer_reset,consumer_reset;
    wire [4:0] producer_pending,consumer_context,orphan,replay;
    wire [3:0] producer_id[5],consumer_id[5];
    for(genvar i=0;i<5;i++)begin:cases
        assign producer_reset[i]=global_reset || (event_reset && i==1);
        assign consumer_reset[i]=global_reset || event_reset;
        reset_path #(.EVENT_PROFILE(i>=3),.ALLOW_REPLAY(i==4)) dut(
            .clk(clk),.producer_reset(producer_reset[i]),.consumer_reset(consumer_reset[i]),
            .issue(issue),.deliver(deliver_all || (drain && i==2)),
            .producer_pending(producer_pending[i]),.consumer_context(consumer_context[i]),
            .producer_id(producer_id[i]),.consumer_id(consumer_id[i]),.orphan(orphan[i]),.replay(replay[i]));
        initial $display("CONFIG %0d %0d %0d %0d %0d",i,i>=3,i==4,i==1,i==2);
    end
    task automatic tick;
        #1;if(clock_available)clk=1;#1;clk=0;#1;
    endtask
    task automatic sample(input int phase);
        for(int i=0;i<5;i++)
            $display("RESET %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",i,phase,
                producer_pending[i],consumer_context[i],producer_id[i],consumer_id[i],orphan[i],replay[i],
                producer_reset[i],consumer_reset[i],!issue&&!deliver_all&&!drain,!consumer_reset[i],i==4&&!consumer_reset[i],clock_available,root_edges);
    endtask
    initial begin
        #1;global_reset=1;tick();global_reset=0;issue=1;tick();issue=0;
        drain=1;tick();drain=0;#1;sample(0);
        event_reset=1;tick();sample(1);
        event_reset=0;#1;sample(2);
        deliver_all=1;tick();deliver_all=0;tick();sample(3);
        $finish;
    end
endmodule
