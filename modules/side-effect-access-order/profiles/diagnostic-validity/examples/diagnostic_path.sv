module diagnostic_path(input logic clk,reset,valid,input logic [3:0] command,
    input logic [7:0] cause_mask,input logic read_clears,status_reset_clears,saved_reset_clears,
    output logic [7:0] status=0,epoch=0,saved_value=0,saved_epoch=0,rd_data=0,rd_epoch=0,
    output logic saved_valid=0,rd_valid=0,accepted=0,access_error=0,path_available=1,
    save_done=0,recovery_seen=0,clear_seen=0);
    // Owned sampled cause latch, diagnostic bus enable and last-response capture.
    // No physical clock gating, metastability, concurrent arrivals or crash firmware.
    always @(posedge clk or posedge reset)begin
        if(reset)begin
            status<=0;epoch<=0;saved_value<=0;saved_epoch<=0;saved_valid<=0;rd_data<=0;rd_epoch<=0;rd_valid<=0;
            accepted<=0;access_error<=0;path_available<=1;save_done<=0;recovery_seen<=0;clear_seen<=0;
        end else begin
            accepted<=0;access_error<=0;save_done<=0;recovery_seen<=0;clear_seen<=0;
            if(valid)case(command)
                1:status<=status|cause_mask;
                2,8:begin
                    rd_valid<=0;
                    if(path_available)begin
                        accepted<=1;rd_valid<=1;rd_data<=status;rd_epoch<=epoch;
                        if(read_clears)begin status<=0;epoch<=epoch+1'b1;clear_seen<=1;end
                    end else access_error<=1;
                end
                3:if(rd_valid && path_available)begin
                    saved_value<=rd_data;saved_epoch<=rd_epoch;saved_valid<=1;accepted<=1;save_done<=1;
                end
                4:begin
                    recovery_seen<=1;rd_valid<=0;rd_data<=0;rd_epoch<=0;
                    if(status_reset_clears)begin status<=0;epoch<=epoch+1'b1;clear_seen<=1;end
                    if(saved_reset_clears)begin saved_valid<=0;saved_value<=0;saved_epoch<=0;end
                end
                5:path_available<=0;
                6:path_available<=1;
                7:begin
                    rd_valid<=0;
                    if(path_available)begin accepted<=1;rd_valid<=1;rd_data<=saved_value;rd_epoch<=saved_epoch;end
                    else access_error<=1;
                end
                9:begin saved_valid<=1;saved_value<=cause_mask;saved_epoch<=99;end
                default:begin end
            endcase
        end
    end
endmodule

module diagnostic_top;
    logic clk=0,reset=0,valid=0;logic [3:0] command=0;
    logic [7:0] cause_mask=1;logic read_clears=1,status_reset_clears=1,saved_reset_clears=0;
    wire [7:0] status,epoch,saved_value,saved_epoch,rd_data,rd_epoch;
    wire saved_valid,rd_valid,accepted,access_error,path_available,save_done,recovery_seen,clear_seen;
    int scenario,seq;
    diagnostic_path path(.*);
    task automatic tick;#1;clk=1;#1;clk=0;#1;endtask
    task automatic observe;
        $display("DIAG %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,$time,command,
            status,epoch,saved_value,saved_epoch,saved_valid,rd_data,rd_epoch,rd_valid,accepted,access_error,path_available,save_done,recovery_seen,clear_seen);seq++;
    endtask
    task automatic step(input int op);command=4'(op);valid=1;tick();observe();valid=0;endtask
    initial begin
        for(int c=0;c<11;c++)begin
            scenario=c;cause_mask=c>=8?4:1;read_clears=c<8;status_reset_clears=!(c==8||c==10);saved_reset_clears=c==7;
            $display("CONFIG %0d %0d %0d %0d %0d",scenario,cause_mask,read_clears,status_reset_clears,saved_reset_clears);
            valid=0;command=0;seq=0;reset=1;tick();reset=0;observe();
            case(c)
                0,7:begin step(1);step(2);step(3);step(4);step(7);end
                1,2,8,9:begin step(1);step(4);step(2);end
                3:begin step(1);step(8);step(2);end
                4:begin step(1);step(5);step(2);end
                5:begin step(0);step(2);end
                6:begin step(9);step(4);step(7);end
                10:begin step(0);step(4);step(2);end
            endcase
        end
        $finish;
    end
endmodule
