#include "Vtop.h"
#include "verilated.h"
#include "ports.hpp"
#include <cstdio>
#include <vector>
int main(int argc,char**argv){
 if(argc!=5)return 3;unsigned f[4];
 for(unsigned i=0;i<4;++i){if(argv[i+1][1] || argv[i+1][0]<'0' || argv[i+1][0]>'3')return 3;f[i]=argv[i+1][0]-'0';}
 if(f[0]>1 || f[3]>1)return 3;
 const unsigned period=FAST_PERIOD*(f[0]?4:1),half=period/2,wanted=f[0]?9:2,cycles=f[0]?9:18;
 VerilatedContext context;Vtop d{&context};unsigned checks=0,failures=0,ideal_l=0,ideal_c=0;std::vector<unsigned> pulses;
 d.P_CLOCK=0;d.P_RESET=RESET_RELEASED;d.P_SHIFT=f[0];d.P_VARIANT=f[1];d.P_START=0;d.P_DATA=1;d.P_SERIAL_IN=0;d.P_SCAN_ENABLE=f[0]?1:unsigned(f[2]!=0);d.eval();
 d.P_RESET=!RESET_RELEASED;d.eval();d.P_RESET=f[3]?!RESET_RELEASED:RESET_RELEASED;d.P_START=1;d.eval();
 std::printf("TIME_UNITS %d %d\nCONFIG %u %u %u %u %u %u %u %u %u\n",context.timeunit(),context.timeprecision(),f[0],f[1],f[2],f[3],FAST_PERIOD,period,half,wanted,cycles);
 if(context.timeunit()!=-9 || context.timeprecision()!=-9)return 3;
 unsigned previous_clock=0,last_reset=0,last_se=0,previous_reset=d.P_RESET,previous_se=d.P_SCAN_ENABLE;
 auto print=[&](unsigned tick){std::printf("SAMPLE %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u %u\n",tick,unsigned(d.P_CLOCK),unsigned(d.P_SLOT),unsigned(d.P_ENABLE),unsigned(d.P_GENERATED_CLOCK),unsigned(d.P_RESET),unsigned(d.P_RESET_N),unsigned(d.P_SCAN_ENABLE),unsigned(d.P_SHIFT),unsigned(d.P_VARIANT),unsigned(d.P_START),unsigned(d.P_DATA),unsigned(d.P_SERIAL_IN),unsigned(d.P_LAUNCH),unsigned(d.P_CAPTURE),ideal_l,ideal_c,checks,failures);};
 print(0);
 for(unsigned step=1;step<=cycles*period;++step){
  context.timeInc(1);const unsigned tick=context.time();
  d.P_CLOCK=(tick%period)>=half;d.P_START=tick<=period;d.P_SERIAL_IN=f[0]?((tick/period)&1u):0;
  unsigned se=f[0]?1:0;
  if(!f[0] && f[2]==1)se=1;
  if(!f[0] && f[2]==2)se=tick<2*period+half-1;
  if(!f[0] && f[2]==3)se=tick<2*period;
  d.P_SCAN_ENABLE=se;d.eval();
  if(unsigned(d.P_RESET)!=previous_reset)last_reset=tick;
  if(unsigned(d.P_SCAN_ENABLE)!=previous_se)last_se=tick;
  previous_reset=d.P_RESET;previous_se=d.P_SCAN_ENABLE;
  if(d.P_GENERATED_CLOCK && !previous_clock){
   pulses.push_back(tick);ideal_c=ideal_l;ideal_l=f[0]?unsigned(d.P_SERIAL_IN):1;
   ++checks;failures+=unsigned(d.P_LAUNCH)!=ideal_l;
   ++checks;failures+=unsigned(d.P_CAPTURE)!=ideal_c;
   ++checks;failures+=unsigned(d.P_RESET)!=RESET_RELEASED || unsigned(d.P_RESET_N)!=1 || unsigned(d.P_SCAN_ENABLE)!=f[0] || tick-last_reset<half || tick-last_se<half;
  }
  previous_clock=d.P_GENERATED_CLOCK;print(tick);
 }
 ++checks;failures+=pulses.size()!=wanted;
 if(f[0]){for(unsigned i=1;i<pulses.size();++i){++checks;failures+=pulses[i]-pulses[i-1]!=period;}}
 else if(pulses.size()==2){++checks;failures+=pulses[1]-pulses[0]!=period;}
 std::printf("PULSES %zu",pulses.size());for(unsigned tick:pulses)std::printf(" %u",tick);
 std::printf("\nNATIVE_RESULT %u %u %u %zu\n",cycles*period+1,checks,failures,pulses.size());d.final();return failures?1:0;
}
