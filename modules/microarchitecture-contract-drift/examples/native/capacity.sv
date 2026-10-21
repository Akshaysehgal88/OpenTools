// Owned bounded credit-window and live-tag examples. No retirement in the window.
module capacity_case #(
  parameter int CAPACITY = 8,
  parameter int ISSUE_LIMIT = 8,
  parameter int RESERVED = 0,
  parameter int PROFILE = 0
);
  localparam int AVAILABLE = CAPACITY - RESERVED;
  bit clk = 0;
  bit reset = 1;
  bit issue = 0;
  int accepted = 0;
  int violations = 0;
  int used = 0;
  int next_tag = 0;
  bit [AVAILABLE-1:0] busy = '0;
  always #1 clk = ~clk;
  always @(posedge clk) begin
    if (reset) begin
      accepted = 0;
      violations = 0;
      used = 0;
      next_tag = 0;
      busy = '0;
    end else if (issue) begin
      if (PROFILE == 0) begin
        if (used == AVAILABLE) violations = violations + 1;
        else begin
          used = used + 1;
          accepted = accepted + 1;
        end
      end else begin
        if (busy[next_tag]) violations = violations + 1;
        else begin
          busy[next_tag] = 1;
          accepted = accepted + 1;
        end
        next_tag = (next_tag + 1) % AVAILABLE;
      end
    end
  end
  initial begin
    if (AVAILABLE <= 0 || ISSUE_LIMIT < 0 || PROFILE < 0 || PROFILE > 1)
      $fatal(1, "Unsupported example configuration");
    @(negedge clk);
    reset = 0;
    issue = 1;
    repeat (ISSUE_LIMIT) @(negedge clk);
    issue = 0;
    $display("OT_RESULT {\"issued\":%0d,\"accepted\":%0d,\"violations\":%0d,\"profile\":%0d}",
             ISSUE_LIMIT, accepted, violations, PROFILE);
    $finish;
  end
endmodule
