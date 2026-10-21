// Owned single-outstanding interface: receipt, completion and discard are distinct.
module handshake_client #(parameter int BAD_ACK=0, BAD_CANCEL=0)(
  input logic drive_request, drive_cancel, accepted_i, completed_i, discarded_i,
  output logic req_o, cancel_o, done_o, discarded_o
);
  assign req_o = drive_request;
  assign cancel_o = drive_cancel;
  assign done_o = BAD_ACK ? accepted_i : completed_i;
  assign discarded_o = BAD_CANCEL ? drive_cancel : discarded_i;
endmodule
module handshake_worker(
  input logic clk, req_i, cancel_i,
  output bit accepted_o=0, completed_o=0, discarded_o=0, committed_o=0
);
  bit inflight=0, started=0;
  int age=0;
  always @(posedge clk) begin
    accepted_o=0;
    completed_o=0;
    discarded_o=0;
    if (req_i && !inflight && !started) begin
      accepted_o=1;
      inflight=1;
      started=1;
      age=0;
    end
    if (cancel_i && inflight && !committed_o) begin
      discarded_o=1;
      inflight=0;
    end else if (inflight) begin
      age=age+1;
      if (age==2) committed_o=1;
      if (age==4) begin
        completed_o=1;
        inflight=0;
      end
    end
  end
endmodule
module behavior_top #(
  parameter int BAD_ACK=0, BAD_CANCEL=0, PULSE_REQUEST=0, CANCEL_CYCLE=3
);
  bit clk=0, drive_request=0, drive_cancel=0;
  wire request_net, cancel_net, accepted_net, completed_net, discarded_net;
  wire committed, client_done, client_discarded;
  int premature=0, false_discard=0;
  handshake_client #(.BAD_ACK(BAD_ACK),.BAD_CANCEL(BAD_CANCEL)) client(
    .drive_request(drive_request),.drive_cancel(drive_cancel),
    .accepted_i(accepted_net),.completed_i(completed_net),.discarded_i(discarded_net),
    .req_o(request_net),.cancel_o(cancel_net),.done_o(client_done),.discarded_o(client_discarded));
  handshake_worker worker(.clk(clk),.req_i(request_net),.cancel_i(cancel_net),
    .accepted_o(accepted_net),.completed_o(completed_net),.discarded_o(discarded_net),.committed_o(committed));
  initial begin
    for (int cycle=1;cycle<=9;cycle=cycle+1) begin
      drive_request=PULSE_REQUEST ? cycle==1 : cycle<=2;
      drive_cancel=cycle==CANCEL_CYCLE;
      #1;clk=1;#1;
      if (client_done && !completed_net) premature=premature+1;
      if (client_discarded && committed) false_discard=false_discard+1;
      $display("OT_EVENT {\"cycle\":%0d,\"request\":%0d,\"accepted\":%0d,\"committed\":%0d,\"completed\":%0d,\"cancel\":%0d,\"server_discarded\":%0d,\"client_done\":%0d,\"client_discarded\":%0d}",
        cycle,request_net,accepted_net,committed,completed_net,cancel_net,discarded_net,client_done,client_discarded);
      clk=0;
    end
    $display("OT_RESULT {\"premature_completion\":%0d,\"false_discard\":%0d}",premature,false_discard);
    $finish;
  end
endmodule
