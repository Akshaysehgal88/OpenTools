module top(input clk,input reset_n,input fun_enable,input test_mode,input da,input db,output gclk_obs,output q0,output q1);
wire qualified_enable,data_buffer,active_base,reset_released;
assign active_base=fun_enable;assign reset_released=reset_n;
ECO_OR allow(.A(active_base),.B(test_mode),.Y(qualified_enable));
ECO_AND gate(.A(clk),.B(qualified_enable),.Y(gclk_obs));
ECO_BUF buffer(.A(q0),.Y(data_buffer));
ECO_DFF launch(.CK(gclk_obs),.RN(reset_released),.D(da),.Q(q0));
ECO_DFF capture(.CK(gclk_obs),.RN(reset_released),.D(data_buffer),.Q(q1));
endmodule
