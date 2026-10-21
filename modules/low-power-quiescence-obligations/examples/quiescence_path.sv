module quiescence_path #(parameter bit LOCAL_ONLY=0,POWER_MODE=1,NO_ISOLATION=0,BAD_ADMISSION=0)(
    input logic root_clk,reset,issue,transfer,sleep_request,return_ready,
    output logic local_pending=0,remote_pending=0,ingress_closed=0,drain_ack=0,
    isolation_active=0,clock_enable=1,power_available=1,
    output integer accepted=0,handed=0,returned=0,received=0,domain_edges=0);
    // Digital availability gate; this fixture does not model ICG or power cells.
    wire domain_clk=root_clk & clock_enable & power_available;
    wire admission=issue && (!sleep_request || BAD_ADMISSION);
    wire handoff=transfer && local_pending;
    always @(posedge domain_clk or posedge reset)
        if(reset)begin local_pending<=0;accepted<=0;handed<=0;received<=0;domain_edges<=0;end
        else begin
            domain_edges<=domain_edges+1;
            if(admission)begin local_pending<=1;accepted<=accepted+1;end
            if(handoff)begin local_pending<=0;handed<=handed+1;end
            if(remote_pending && return_ready)received<=received+1;
        end
    // External owner stays on root clock. Return needs a live receiver edge.
    always @(posedge root_clk or posedge reset)
        if(reset)begin remote_pending<=0;returned<=0;end
        else if(handoff)remote_pending<=1;
        else if(remote_pending && return_ready && clock_enable && power_available)begin
            remote_pending<=0;returned<=returned+1;end
    // Always-on sequencer; LOCAL_ONLY deliberately ignores the external owner.
    always @(posedge root_clk or posedge reset)
        if(reset)begin ingress_closed<=0;drain_ack<=0;isolation_active<=0;clock_enable<=1;power_available<=1;end
        else begin
            ingress_closed<=sleep_request;
            if(sleep_request && !drain_ack && !local_pending && (LOCAL_ONLY || (!remote_pending && ingress_closed)))drain_ack<=1;
            if(POWER_MODE && !NO_ISOLATION && drain_ack)isolation_active<=1;
            if(drain_ack && (!POWER_MODE || NO_ISOLATION || isolation_active))clock_enable<=0;
            if(POWER_MODE && !clock_enable)power_available<=0;
        end
endmodule

module quiescence_top;
    logic root_clk=0,reset=0,issue=0,transfer=0,sleep_request=0;
    logic [5:0] return_ready=0;
    wire [5:0] local_pending,remote_pending,ingress_closed,drain_ack,isolation_active,clock_enable,power_available;
    wire integer accepted[6],handed[6],returned[6],received[6],domain_edges[6];
    for(genvar i=0;i<6;i++)begin:cases
        localparam bit LOCAL_ONLY=(i==0 || i==2);
        localparam bit POWER_MODE=(i!=2 && i!=3);
        quiescence_path #(.LOCAL_ONLY(LOCAL_ONLY),.POWER_MODE(POWER_MODE),.NO_ISOLATION(i==4),.BAD_ADMISSION(i==5)) dut(
            .root_clk(root_clk),.reset(reset),.issue(issue),.transfer(transfer),.sleep_request(sleep_request),.return_ready(return_ready[i]),
            .local_pending(local_pending[i]),.remote_pending(remote_pending[i]),.ingress_closed(ingress_closed[i]),.drain_ack(drain_ack[i]),
            .isolation_active(isolation_active[i]),.clock_enable(clock_enable[i]),.power_available(power_available[i]),
            .accepted(accepted[i]),.handed(handed[i]),.returned(returned[i]),.received(received[i]),.domain_edges(domain_edges[i]));
        initial $display("CONFIG %0d %0d %0d %0d %0d",i,LOCAL_ONLY,POWER_MODE,i==4,i==5);
    end
    task automatic tick;
        #1;root_clk=1;#1;root_clk=0;#1;
    endtask
    initial begin
        #1;reset=1;tick();reset=0;
        for(int step=0;step<12;step++)begin
            issue=(step==1 || step==8);transfer=(step==2);sleep_request=(step>=3);
            for(int i=0;i<6;i++)return_ready[i]=(step>=((i==2 || i==3)?7:6));
            tick();
            for(int i=0;i<6;i++)
                $display("QUIESCENCE %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",i,step,$time,
                    local_pending[i],remote_pending[i],ingress_closed[i],drain_ack[i],isolation_active[i],clock_enable[i],power_available[i],
                    accepted[i],handed[i],returned[i],received[i],domain_edges[i],issue,transfer,sleep_request,return_ready[i]);
        end
        $finish;
    end
endmodule
