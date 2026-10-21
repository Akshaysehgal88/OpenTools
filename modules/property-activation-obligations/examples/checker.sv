module activation_checker(input checker_clk, reset, mode, extra_disable, event_req, condition_ok);
  always @(posedge checker_clk)
    $display("SAMPLE %m %0t %0d %0d %0d %0d %0d", $time, reset, mode, extra_disable, event_req, condition_ok);
  p_transition: assert property (@(posedge checker_clk) disable iff (reset || extra_disable) event_req |-> condition_ok)
    else $display("ASSERT_FAIL %m %0t", $time);
  c_active_any: cover property (@(posedge checker_clk) !reset && !extra_disable && event_req);
  c_active_normal: cover property (@(posedge checker_clk) !reset && !extra_disable && !mode && event_req);
  c_active_risk: cover property (@(posedge checker_clk) !reset && !extra_disable && mode && event_req);
endmodule

// This observer is bound independently of the checker and never disables on mode.
module obligation_observer(input observer_clk, reset, mode, event_req, condition_ok);
  always @(posedge observer_clk)
    $display("REQUIRED %m %0t %0d %0d %0d %0d", $time, reset, mode, event_req, condition_ok);
  c_required_normal: cover property (@(posedge observer_clk) !reset && !mode && event_req);
  c_required_risk: cover property (@(posedge observer_clk) !reset && mode && event_req);
endmodule
