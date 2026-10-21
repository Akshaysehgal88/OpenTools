module buffered_publication(input logic clk,reset,valid,flag_io,input logic [3:0] command,pred_mask,succ_mask,
    output logic payload_issued=0,data_pending=0,flag_pending=0,fence_seen=0,fence_has_predecessor=0,flag_guarded=0,
    output logic payload_memory=0,publication_visible=0,consumed=0,rflag=0,rpayload=0,rpayload_valid=0,step_enabled=0);
    // Concrete owned two-queue path, not an ISA memory model. Scalar stores are register updates.
    always @(posedge clk or posedge reset)begin
        if(reset)begin
            payload_issued<=0;data_pending<=0;flag_pending<=0;fence_seen<=0;fence_has_predecessor<=0;flag_guarded<=0;
            payload_memory<=0;publication_visible<=0;consumed<=0;rflag<=0;rpayload<=0;rpayload_valid<=0;step_enabled<=0;
        end else begin
            step_enabled<=0;
            if(valid)case(command)
                1:begin payload_issued<=1;data_pending<=1;step_enabled<=1;end
                2:begin fence_seen<=1;fence_has_predecessor<=payload_issued;step_enabled<=1;end
                3:begin
                    flag_pending<=1;step_enabled<=1;
                    // Mask bits label owned domains I/O/R/W, not executed RISC-V instructions.
                    flag_guarded<=fence_seen && fence_has_predecessor && pred_mask[0] && (flag_io?succ_mask[2]:succ_mask[0]);
                end
                4:if(data_pending)begin payload_memory<=1;data_pending<=0;step_enabled<=1;end
                5:if(flag_pending && (!flag_guarded || !data_pending))begin publication_visible<=1;flag_pending<=0;step_enabled<=1;end
                6:if(!consumed)begin
                    consumed<=1;step_enabled<=1;rflag<=publication_visible;
                    rpayload_valid<=publication_visible;rpayload<=publication_visible?payload_memory:1'b0;
                end
                default:begin end
            endcase
        end
    end
endmodule

module ordering_top;
    logic clk=0,reset=0,valid=0,flag_io=0;logic [3:0] command=0,pred_mask=0,succ_mask=0;
    wire payload_issued,data_pending,flag_pending,fence_seen,fence_has_predecessor,flag_guarded;
    wire payload_memory,publication_visible,consumed,rflag,rpayload,rpayload_valid,step_enabled;
    buffered_publication path(.*);
    int scenario,run_id,seq,placement;
    int schedules[6][3]='{'{4,5,6},'{4,6,5},'{5,4,6},'{5,6,4},'{6,4,5},'{6,5,4}};
    task automatic tick;#1;clk=1;#1;clk=0;#1;endtask
    task automatic observe;
        $display("ORDER %0d %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,run_id,seq,$time,command,
            payload_issued,data_pending,flag_pending,fence_seen,fence_has_predecessor,flag_guarded,payload_memory,
            publication_visible,consumed,rflag,rpayload,rpayload_valid,step_enabled);seq++;
    endtask
    task automatic access(input int op);
        command=4'(op);valid=1;tick();observe();valid=0;
    endtask
    initial begin
        for(int c=0;c<10;c++)begin
            scenario=c;flag_io=c>=2 && c<=8;
            pred_mask=(c==0||c==2||c==9)?0:c==5?15:c==6?4:1;
            succ_mask=(c==0||c==2||c==9)?0:c==5?15:(c==1||c==3)?1:4;
            placement=(c==0||c==2||c==9)?0:c==7?2:c==8?3:1;
            $display("CONFIG %0d %0d %0d %0d %0d",scenario,flag_io,pred_mask,succ_mask,placement);
            for(int r=0;r<(c==9?1:6);r++)begin
                run_id=r;seq=0;valid=0;command=0;reset=1;tick();reset=0;observe();
                if(placement==3)access(2);
                access(1);
                if(placement==1)access(2);
                access(3);
                if(placement==2)access(2);
                for(int action_index=0;action_index<3;action_index++)access(schedules[r][action_index]);
            end
        end
        $finish;
    end
endmodule
