#include "Vtop.h"
#include "verilated.h"
#include "bindings.hpp"
#include <iostream>
int main(){
 VerilatedContext context;Vtop d{&context};
 d.P_CLOCK=0;d.P_RESET=!RESET_ASSERTED;d.P_A=MODE_A;d.P_B=MODE_B;d.P_DA=0;d.P_DB=1;d.eval();
 d.P_RESET=RESET_ASSERTED;d.eval();d.P_RESET=!RESET_ASSERTED;d.eval();
 unsigned pulses=0;bool prior=0;
 std::cout<<"FORMAT opentools.eco-clock.v1\nCONFIG "<<CYCLES<<' '<<RESET_ASSERTED<<' '<<MODE_A<<' '<<MODE_B<<"\n";
 const unsigned pattern[]={0,1,1,0,1,0,0,1};
 for(unsigned tick=0;tick<2*CYCLES;++tick){
  d.P_DA=pattern[(tick/2)%8];d.P_DB=!d.P_DA;d.P_CLOCK=tick%2;context.timeInc(1);d.eval();
  pulses+=!prior&&d.P_GCLK;prior=d.P_GCLK;
  std::cout<<"SAMPLE "<<tick<<' '<<unsigned(d.P_CLOCK)<<' '<<unsigned(d.P_RESET)<<' '<<unsigned(d.P_A)<<' '<<unsigned(d.P_B)<<' '<<unsigned(d.P_DA)<<' '<<unsigned(d.P_DB)<<' '<<unsigned(d.P_GCLK)<<' '<<unsigned(d.P_Q0)<<' '<<unsigned(d.P_Q1)<<'\n';
 }
 std::cout<<"CLOCK_RESULT "<<CYCLES<<' '<<pulses<<' '<<(pulses==CYCLES?"PASS":"FAIL")<<'\n';d.final();return pulses==CYCLES?0:1;
}
