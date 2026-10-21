module ownership_transfer(input logic clk,reset,valid,grant_ready,input logic [1:0] guard_mode,
    input logic [3:0] operation,input logic [2:0] source_id,input logic [7:0] message_id,message_epoch,
    output logic active=0,data_valid=0,granted=0,writer_permission=0,offer_pending=0,
    output logic offered=0,grant_accepted=0,message_accepted=0,read_valid=0,write_committed=0,stable_label=0,
    output logic [1:0] old_permissions=3,pending_mask=0,pending_count=0,
    output logic [31:0] transfer_data=0,new_cache=0,read_data=0,
    output logic [7:0] active_id=0,active_epoch=0);
    // One owned resource, two old read claims, one requester. No arrivals/reset during transfer.
    logic match_message,legal_grant,offer_now;
    always_comb begin
        match_message=active && message_id==active_id && message_epoch==active_epoch;
        legal_grant=guard_mode==1 || (data_valid && (guard_mode==2?pending_count==0:pending_mask==0));
        offer_now=active && !granted && legal_grant && (offer_pending || valid && operation==4);
    end
    always @(posedge clk or posedge reset)begin
        if(reset)begin
            active<=0;data_valid<=0;granted<=0;writer_permission<=0;offer_pending<=0;
            offered<=0;grant_accepted<=0;message_accepted<=0;read_valid<=0;write_committed<=0;stable_label<=0;
            old_permissions<=3;pending_mask<=0;pending_count<=0;transfer_data<=0;new_cache<=0;read_data<=0;active_id<=0;active_epoch<=0;
        end else begin
            offered<=offer_now;grant_accepted<=offer_now && grant_ready;
            message_accepted<=0;read_valid<=0;write_committed<=0;read_data<=0;
            if(offer_now && grant_ready)begin
                granted<=1;writer_permission<=1;stable_label<=1;offer_pending<=0;
                new_cache<=data_valid?transfer_data:32'd0;
            end else if(valid && operation==4 && active && !granted)offer_pending<=1;
            if(valid)case(operation)
                1:begin active<=1;active_id<=message_id;active_epoch<=message_epoch;pending_mask<=old_permissions;
                    pending_count<=2'(int'(old_permissions[0])+int'(old_permissions[1]));message_accepted<=1;end
                2:if(match_message)begin transfer_data<=17;data_valid<=1;message_accepted<=1;end
                3:if(match_message && source_id<2)begin
                    message_accepted<=1;old_permissions[source_id]<=0;pending_mask[source_id]<=0;
                    // Deliberate count-only bug: duplicate source can discharge the numerical count twice.
                    if(guard_mode==2)begin if(pending_count!=0)pending_count<=pending_count-1;end
                    else if(pending_mask[source_id])pending_count<=pending_count-1;
                end
                5:if(writer_permission)begin read_valid<=1;read_data<=new_cache;end
                6:if(writer_permission)begin new_cache<=165;write_committed<=1;end
                7:if(source_id<2 && old_permissions[source_id])begin read_valid<=1;read_data<=17;end
                8:if(granted)begin active<=0;message_accepted<=1;end
                default:begin end
            endcase
        end
    end
endmodule

module transition_top;
    logic clk=0,reset=0,valid=0,grant_ready=0;
    logic [1:0] guard_mode=0;logic [3:0] operation=0;logic [2:0] source_id=4;
    logic [7:0] message_id=7,message_epoch=1;
    wire active,data_valid,granted,writer_permission,offer_pending,offered,grant_accepted,message_accepted,read_valid,write_committed,stable_label;
    wire [1:0] old_permissions,pending_mask,pending_count;
    wire [31:0] transfer_data,new_cache,read_data;wire [7:0] active_id,active_epoch;
    ownership_transfer transfer(.*);
    int scenario,seq;
    task automatic tick;#1;clk=1;#1;clk=0;#1;endtask
    task automatic observe;
        $display("TRANSFER %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,$time,
            operation,source_id,message_id,message_epoch,grant_ready,active,data_valid,granted,writer_permission,offer_pending,
            offered,grant_accepted,message_accepted,read_valid,write_committed,stable_label,old_permissions,pending_mask,pending_count,
            transfer_data,new_cache,read_data,active_id,active_epoch,guard_mode);seq++;
    endtask
    task automatic access(input int op,source,epoch,input logic ready);
        operation=4'(op);source_id=3'(source);message_id=7;message_epoch=8'(epoch);grant_ready=ready;valid=1;tick();observe();valid=0;
    endtask
    initial begin
        for(int c=0;c<8;c++)begin
            scenario=c;seq=0;valid=0;grant_ready=0;operation=0;source_id=4;message_id=7;message_epoch=1;
            guard_mode=(c==0||c==2||c==5)?1:(c==3)?2:0;
            $display("CONFIG %0d %0d",scenario,guard_mode);reset=1;tick();reset=0;observe();
            access(1,2,1,0);
            if(c!=2)access(2,3,1,0);
            if(c==4)access(3,0,0,0); // stale identity must not discharge this transfer
            access(3,0,1,0);
            if(c==3)access(3,0,1,0); // duplicate source fools only the numerical guard
            if(c==1||c==2||c==4||c==6||c==7)access(3,1,1,0);
            if(c==7)begin access(4,4,1,0);access(0,4,1,0);end // offered, not accepted
            access(4,4,1,1);
            access(5,2,1,0);access(6,2,1,0);access(7,1,1,0);
            if(c==0||c==3||c==5)access(3,1,1,0);
            if(c==2)access(2,3,1,0);
            access(8,2,1,0);
        end
        $finish;
    end
endmodule
