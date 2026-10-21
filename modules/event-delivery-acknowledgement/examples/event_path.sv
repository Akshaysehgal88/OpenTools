module event_path #(parameter bit HELD=1, CLEAR_SOURCE=1)(
    input logic root_clk,reset,functional_enable,aon_enable,fire,power_available,
    interrupt_enable,route_selected,wake_enable,sleep_window,service_enable,
    output logic source_status=0,interrupt_pending=0,wake_pending=0,
    output integer assertions=0,irq_captures=0,deliveries=0,services=0,source_clears=0,
    wake_captures=0,wake_requests=0,functional_edges=0,aon_edges=0);
    // Owned low-phase gate convention, not a reference ICG or CDC implementation.
    wire functional_clk=root_clk & functional_enable & power_available;
    wire aon_clk=root_clk & aon_enable;
    logic seen=0,in_service=0,clear_request=0,wake_sent=0;
    always @(posedge root_clk or posedge reset)
        if(reset)begin source_status<=0;assertions<=0;source_clears<=0;end
        else if(fire)begin source_status<=1;assertions<=assertions+1;end
        else if(!HELD)source_status<=0;
        else if(clear_request && source_status)begin source_status<=0;source_clears<=source_clears+1;end
    // Sample a high level once, rearming only after a sampled low level.
    always @(posedge functional_clk or posedge reset)
        if(reset)begin interrupt_pending<=0;seen<=0;in_service<=0;clear_request<=0;
            irq_captures<=0;deliveries<=0;services<=0;functional_edges<=0;end
        else begin
            functional_edges<=functional_edges+1;clear_request<=0;
            if(!source_status)seen<=0;
            if(source_status && !seen && interrupt_enable && route_selected)begin
                interrupt_pending<=1;seen<=1;irq_captures<=irq_captures+1;end
            if(interrupt_pending && !in_service)begin
                interrupt_pending<=0;in_service<=1;deliveries<=deliveries+1;end
            if(in_service && service_enable)begin
                in_service<=0;services<=services+1;clear_request<=CLEAR_SOURCE;end
        end
    always @(posedge aon_clk or posedge reset)
        if(reset)begin wake_pending<=0;wake_sent<=0;wake_captures<=0;wake_requests<=0;aon_edges<=0;end
        else begin
            aon_edges<=aon_edges+1;
            if(source_status && wake_enable && !wake_pending)begin wake_pending<=1;wake_captures<=wake_captures+1;end
            if(wake_pending && sleep_window && !wake_sent)begin wake_sent<=1;wake_requests<=wake_requests+1;end
        end
endmodule

module event_top;
    logic root_clk=0,reset=0,fire=0,sleep_window=0;
    logic [5:0] functional_enable='1,aon_enable='1;
    wire [5:0] source_status,interrupt_pending,wake_pending;
    wire integer assertions[6],irq_captures[6],deliveries[6],services[6],source_clears[6],
        wake_captures[6],wake_requests[6],functional_edges[6],aon_edges[6];
    for(genvar i=0;i<6;i++)begin:cases
        localparam bit HELD=(i!=2 && i!=4);
        localparam bit CLEAR_SOURCE=(i!=5);
        event_path #(.HELD(HELD),.CLEAR_SOURCE(CLEAR_SOURCE)) dut(
            .root_clk(root_clk),.reset(reset),.functional_enable(functional_enable[i]),.aon_enable(aon_enable[i]),
            .fire(fire),.power_available(1'b1),.interrupt_enable(1'b1),.route_selected(1'b1),.wake_enable(1'b1),
            .sleep_window(sleep_window),.service_enable(1'b1),.source_status(source_status[i]),
            .interrupt_pending(interrupt_pending[i]),.wake_pending(wake_pending[i]),.assertions(assertions[i]),
            .irq_captures(irq_captures[i]),.deliveries(deliveries[i]),.services(services[i]),.source_clears(source_clears[i]),
            .wake_captures(wake_captures[i]),.wake_requests(wake_requests[i]),.functional_edges(functional_edges[i]),.aon_edges(aon_edges[i]));
        initial $display("CONFIG %0d %0d %0d %0d %0d",i,HELD,CLEAR_SOURCE,i>=2&&i<=4,i==0);
    end
    task automatic tick;
        #1;root_clk=1;#1;root_clk=0;#1;
    endtask
    initial begin
        #1;reset=1;tick();reset=0;
        for(int step=0;step<12;step++)begin
            fire=(step==2);sleep_window=(step<=10);
            for(int i=0;i<6;i++)begin
                functional_enable[i]=!((i>=2 && i<=4) && step>=2 && step<=4);
                aon_enable[i]=(i!=0 || step>=9);
            end
            tick();
            for(int i=0;i<6;i++)
                $display("EVENT %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d 1 1 1 1 %0d",i,step,$time,
                    source_status[i],interrupt_pending[i],wake_pending[i],assertions[i],irq_captures[i],deliveries[i],services[i],source_clears[i],
                    wake_captures[i],wake_requests[i],functional_edges[i],aon_edges[i],functional_enable[i],aon_enable[i],sleep_window);
        end
        $finish;
    end
endmodule
