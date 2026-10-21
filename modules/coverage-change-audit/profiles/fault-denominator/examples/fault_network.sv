// Owned combinational injection-site model; not a full netlist pin fault census.
module fault_network #(parameter int FAMILY=0,N=FAMILY?4:3,S=FAMILY?6:5,O=FAMILY?2:1)(
 input logic [N-1:0] stimulus,input logic test_mode,fault_enable,
 input logic [3:0] fault_site,input logic stuck_value,
 output logic [S-1:0] raw_sites,driven_sites,output logic [O-1:0] observed);
 function automatic logic injected(input logic value,input int site);
   return fault_enable && fault_site==site ? stuck_value : value;
 endfunction
 if(FAMILY==0)begin:select_path
   assign raw_sites[0]=stimulus[0]&stimulus[1];
   assign raw_sites[1]=stimulus[0]|stimulus[1];
   assign raw_sites[2]=stimulus[2]?driven_sites[0]:driven_sites[1];
   assign raw_sites[3]=driven_sites[2];
   assign raw_sites[4]=1'b0;
   assign observed[0]=test_mode?driven_sites[0]:driven_sites[3];
 end else begin:qualifier_path
   assign raw_sites[0]=stimulus[0]^stimulus[1];
   assign raw_sites[1]=stimulus[2]&stimulus[3];
   assign raw_sites[2]=driven_sites[0]&driven_sites[1];
   assign raw_sites[3]=driven_sites[0]|driven_sites[1];
   assign raw_sites[4]=driven_sites[2];
   assign raw_sites[5]=1'b0;
   assign observed={test_mode?driven_sites[2]:driven_sites[3],driven_sites[4]};
 end
 for(genvar i=0;i<S;i++)assign driven_sites[i]=injected(raw_sites[i],i);
endmodule
