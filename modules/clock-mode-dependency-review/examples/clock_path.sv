module clock_path #(parameter bit BAD=0, WAKE=0)(
    input logic root,reset,request,restore_ready,
    output logic gate_enabled=0,worker_ready=0,transition_done=0,
    output integer worker_edges=0);
    wire worker_clk=root & gate_enabled;
    // enable-gate: the sequencer itself stays on the root clock.
    // Falling-edge update is an owned fixture convention, not a qualified ICG cell.
    always @(negedge root or posedge reset)
        if(reset)gate_enabled<=0;
        else gate_enabled<=request && (!WAKE || restore_ready) && (!BAD || worker_ready);
    // worker-ack: this acknowledgement needs actual worker-clock edges.
    always @(posedge worker_clk or posedge reset)
        if(reset)begin worker_ready<=0;worker_edges<=0;end
        else begin
            worker_edges<=worker_edges+1;
            if(request && (!WAKE || worker_edges>=1))worker_ready<=1;
        end
    // release-wait: the root-clock controller waits for the worker.
    always @(posedge root or posedge reset)
        if(reset)transition_done<=0;
        else if(worker_ready)transition_done<=1;
endmodule

module clock_top;
    logic root=0,reset=0,request=0;
    wire [4:0] gate_enabled,worker_ready,transition_done;
    wire integer worker_edges[5];
    for(genvar i=0;i<5;i++)begin:cases
        localparam bit IS_WAKE=(i>=2);
        localparam bit IS_BAD=(i==0 || i==2);
        clock_path #(.BAD(IS_BAD),.WAKE(IS_WAKE)) dut(
            .root(root),.reset(reset),.request(request),.restore_ready(i!=4),
            .gate_enabled(gate_enabled[i]),.worker_ready(worker_ready[i]),
            .transition_done(transition_done[i]),.worker_edges(worker_edges[i]));
        initial $display("CONFIG %0d %0d %0d %0d",i,IS_BAD,IS_WAKE,i!=4);
    end
    initial begin
        #1;reset=1;#1;root=1;#1;root=0;#1;reset=0;request=1;
        for(int step=0;step<8;step++)begin
            #1;root=1;#1;
            for(int i=0;i<5;i++)
                $display("CLOCK %0d %0d %0d %0d %0d %0d %0d %0d %0d",i,step,reset,request,gate_enabled[i],worker_ready[i],transition_done[i],worker_edges[i],i!=4);
            root=0;#1;
        end
        $finish;
    end
endmodule
