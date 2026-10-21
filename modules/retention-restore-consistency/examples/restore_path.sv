module restore_path #(parameter bit CONTEXT=0,COLD_REINIT=0,parameter logic [4:0] KEEP_MASK=5'b11111)(
    input logic clk,reset,seed,logical_loss,reinitialize,initialize_memory,publish_valid,
    consumer_enabled,power_available,read_request,input logic [3:0] requested_identity,
    output logic [7:0] payload=0,output logic [3:0] identity=0,
    output logic valid=0,auxiliary=0,initialized=0,response_valid=0,read_hit=0,read_error=0,
    output logic [7:0] read_data=0,output integer read_count=0);
    // Selective logical loss fixture, not a retention-cell or UPF implementation.
    always @(posedge clk or posedge reset)
        if(reset)begin payload<=0;identity<=0;valid<=0;auxiliary<=0;initialized<=0;
            response_valid<=0;read_hit<=0;read_error<=0;read_data<=0;read_count<=0;end
        else begin
            response_valid<=0;
            if(seed)begin payload<=CONTEXT?8'h6d:8'ha5;identity<=CONTEXT?4'd9:4'd5;
                valid<=1;auxiliary<=!(CONTEXT || COLD_REINIT);initialized<=1;end
            if(logical_loss)begin
                if(!KEEP_MASK[0])payload<=0;
                if(!KEEP_MASK[1])identity<=0;
                if(!KEEP_MASK[2])valid<=0;
                if(!KEEP_MASK[3])auxiliary<=0;
                if(!KEEP_MASK[4])initialized<=0;
            end
            if(reinitialize)begin payload<=8'h3c;identity<=4'd2;valid<=0;auxiliary<=0;initialized<=1;end
            if(initialize_memory)initialized<=1;
            if(publish_valid)valid<=1;
            if(read_request && consumer_enabled && power_available)begin
                response_valid<=1;read_count<=read_count+1;
                read_hit<=valid && identity==requested_identity;
                read_error<=valid && identity==requested_identity && !initialized;
                read_data<=(valid && identity==requested_identity)?payload:8'h00;
            end
        end
endmodule

module restore_top;
    logic clk=0,reset=0,seed=0,logical_loss=0,power_available=1,consumer_enabled=0,restore_ready=0;
    logic [8:0] reinitialize=0,initialize_memory=0,publish_valid=0,read_request=0;
    wire [7:0] payload[9],read_data[9];
    wire [3:0] identity[9],requested_identity[9];
    wire [8:0] valid,auxiliary,initialized,response_valid,read_hit,read_error;
    wire integer read_count[9];
    for(genvar i=0;i<9;i++)begin:cases
        localparam bit CONTEXT=(i>=7);
        localparam logic [4:0] KEEP=(i==0)?5'd1:(i==1||i==7)?5'd30:(i==3)?5'd23:(i==4)?5'd15:(i==5)?5'd11:(i==6)?5'd0:5'd31;
        assign requested_identity[i]=(i==6)?4'd2:CONTEXT?4'd9:4'd5;
        restore_path #(.CONTEXT(CONTEXT),.COLD_REINIT(i==6),.KEEP_MASK(KEEP)) dut(
            .clk(clk),.reset(reset),.seed(seed),.logical_loss(logical_loss),.reinitialize(reinitialize[i]),
            .initialize_memory(initialize_memory[i]),.publish_valid(publish_valid[i]),.consumer_enabled(consumer_enabled),
            .power_available(power_available),.read_request(read_request[i]),.requested_identity(requested_identity[i]),
            .payload(payload[i]),.identity(identity[i]),.valid(valid[i]),.auxiliary(auxiliary[i]),.initialized(initialized[i]),
            .response_valid(response_valid[i]),.read_hit(read_hit[i]),.read_error(read_error[i]),.read_data(read_data[i]),.read_count(read_count[i]));
        initial $display("CONFIG %0d %0d %0d %0d %0d %0d",i,CONTEXT,KEEP,i==5,i==6,i==4);
    end
    task automatic tick;
        #1;clk=1;#1;clk=0;#1;
    endtask
    initial begin
        #1;reset=1;tick();reset=0;
        for(int step=0;step<12;step++)begin
            seed=(step==1);logical_loss=(step==3);power_available=(step!=3);
            consumer_enabled=(step>=4);restore_ready=(step>=7);
            for(int i=0;i<9;i++)begin
                reinitialize[i]=(i==6 && step==6);
                initialize_memory[i]=(i==5 && step==6)||(i==4 && step==7);
                publish_valid[i]=(i==5 || i==6)&&step==7;
                read_request[i]=(step==((i==4)?5:8));
            end
            tick();
            for(int i=0;i<9;i++)
                $display("RESTORE %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",i,step,$time,
                    payload[i],identity[i],valid[i],auxiliary[i],initialized[i],response_valid[i],read_hit[i],read_error[i],read_data[i],read_count[i],
                    power_available,consumer_enabled,restore_ready,logical_loss,read_request[i],requested_identity[i],
                    initialize_memory[i],reinitialize[i],publish_valid[i],seed);
        end
        $finish;
    end
endmodule
