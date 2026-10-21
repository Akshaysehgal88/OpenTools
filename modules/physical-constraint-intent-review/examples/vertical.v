module top(input ref_clock,input reset,input sleep_req,input wake_test,input source_a,input source_b,output clock_observed,output first_state,output second_state);
wire qualified_enable,data_buffer,active_base,reset_released;
ECO_INV sleep_inverse(.A(sleep_req),.Y(active_base));
ECO_INV reset_inverse(.A(reset),.Y(reset_released));
ECO_OR wake_join(.A(active_base),.B(wake_test),.Y(qualified_enable));
ECO_AND clock_switch(.A(ref_clock),.B(qualified_enable),.Y(clock_observed));
ECO_BUF data_forward(.A(first_state),.Y(data_buffer));
ECO_DFF producer(.CK(clock_observed),.RN(reset_released),.D(source_a),.Q(first_state));
ECO_DFF consumer(.CK(clock_observed),.RN(reset_released),.D(data_buffer),.Q(second_state));
endmodule
