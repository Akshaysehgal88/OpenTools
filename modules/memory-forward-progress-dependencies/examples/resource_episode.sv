module resource_episode(input logic clk,reset,step_valid,input logic [1:0] strategy,selected,
    input logic external_allowed,output logic [2:0] phase_a=0,phase_b=0,
    output logic [2:0] held_a=0,held_b=0,request_a,request_b,
    output logic release_a,release_b,enabled_a,enabled_b,external_enabled,done_a,done_b);
    // Stages: 0 first acquire; 1 retained wait; 2 wait after dropping first;
    // 3 complete/release; 4 done. No timers, cancellation, arrivals or implicit releases.
    function automatic logic [2:0] first(input logic actor);
        return actor && strategy!=3 ? 3'b010 : 3'b001;
    endfunction
    function automatic logic [2:0] second(input logic actor);
        if(!actor || strategy==3)return 3'b010;
        return strategy==1 ? 3'b100 : 3'b001;
    endfunction
    function automatic logic [2:0] request_for(input logic actor,input logic [2:0] phase);
        if(phase==0)return first(actor);
        if(phase==1 && !(strategy==2 && !actor) || phase==2)return second(actor);
        return 0;
    endfunction
    always_comb begin
        request_a=request_for(0,phase_a);request_b=request_for(1,phase_b);
        release_a=phase_a==3 || phase_a==1 && strategy==2;
        release_b=phase_b==3;
        enabled_a=release_a || request_a!=0 && ((held_a|held_b)&request_a)==0;
        enabled_b=release_b || request_b!=0 && ((held_a|held_b)&request_b)==0;
        external_enabled=external_allowed && phase_a==1 && held_a!=0;
        done_a=phase_a==4;done_b=phase_b==4;
    end
    always @(posedge clk or posedge reset)begin
        if(reset)begin phase_a<=0;phase_b<=0;held_a<=0;held_b<=0;end
        else if(step_valid)begin
            if(selected==0 && enabled_a)begin
                case(phase_a)
                    0:begin held_a<=first(0);phase_a<=1;end
                    1:if(strategy==2)begin held_a<=0;phase_a<=2;end
                      else begin held_a<=held_a|second(0);phase_a<=3;end
                    2:begin held_a<=second(0);phase_a<=3;end
                    3:begin held_a<=0;phase_a<=4;end
                    default:begin end
                endcase
            end else if(selected==1 && enabled_b)begin
                case(phase_b)
                    0:begin held_b<=first(1);phase_b<=1;end
                    1:begin held_b<=held_b|second(1);phase_b<=3;end
                    2:begin held_b<=second(1);phase_b<=3;end
                    3:begin held_b<=0;phase_b<=4;end
                    default:begin end
                endcase
            end else if(selected==2 && external_enabled)begin held_a<=0;phase_a<=2;end
        end
    end
endmodule

module episode_top;
    logic clk=0,reset=0,step_valid=0,external_allowed=0;
    logic [1:0] strategy=0,selected=3;
    wire [2:0] phase_a,phase_b,held_a,held_b,request_a,request_b;
    wire release_a,release_b,enabled_a,enabled_b,external_enabled,done_a,done_b;
    resource_episode episode(.*);
    int scenario,seq;
    task automatic tick;
        #1;clk=1;#1;clk=0;#1;
    endtask
    task automatic observe;
        $display("STATE %0d %0d %0t %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",scenario,seq,$time,selected,
            phase_a,phase_b,held_a,held_b,request_a,request_b,release_a,release_b,enabled_a,enabled_b,external_enabled,done_a,done_b);
    endtask
    initial begin
        for(int c=0;c<9;c++)begin
            scenario=c;strategy=(c==1||c==6)?1:(c==2)?2:(c==4)?3:0;
            external_allowed=c==7;selected=3;step_valid=0;reset=1;tick();reset=0;
            $display("CONFIG %0d %0d %0d",scenario,strategy,external_allowed);
            seq=0;observe();
            for(int s=1;s<=12;s++)begin
                seq=s;step_valid=1;
                selected=2'((s-1)%2);
                if(c==5)selected=s<=3?0:s<=6?1:3; // same cyclic design, serialized observed path
                if(c==6 && s>2)selected=0; // B can escape but is never selected again
                if(c==7 && s==3)selected=2;
                tick();observe();
            end
        end
        $finish;
    end
endmodule
