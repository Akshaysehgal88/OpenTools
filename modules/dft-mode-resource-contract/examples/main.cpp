#include "Vtop.h"
#include "verilated.h"
#include "ports.hpp"
#include <cstdio>
#include <stdexcept>
int main(int argc,char**argv){
 try{
  if(argc!=9)throw std::runtime_error("use MASK MFG DEBUG POWER ISO TEST_CLOCK CAPTURE_SE_CORRECT TEST_MODE");
  unsigned f[8];for(unsigned i=0;i<8;++i){if(argv[i+1][1] || (argv[i+1][0]!='0' && argv[i+1][0]!='1'))throw std::runtime_error("Boolean flags required");f[i]=argv[i+1][0]-'0';}
  VerilatedContext context;Vtop dut{&context};unsigned ideal=0,step=0,checks=0,failures=0;
  auto eval=[&](){dut.eval();context.timeInc(1);};
  dut.P_FCLK=0;dut.P_TCLK=0;dut.P_POR=1;dut.P_FUNCTIONAL_RESET=1;dut.P_TEST_MODE=f[7];dut.fixture_reset_mask=f[0];
  dut.P_MANUFACTURING=f[1];dut.P_DEBUG=f[2];dut.P_POWER=f[3];dut.P_ISOLATION=f[4];dut.P_SHIFT_REQUEST=1;dut.P_SERIAL_IN=0;dut.P_PARALLEL_DATA=CAPTURE_WORD;eval();dut.P_POR=0;eval();
  std::printf("CONFIG %u %u %u %u %u %u %u %u %u\n",WIDTH,LOAD_WORD,CAPTURE_WORD,unsigned(dut.P_TEST_MODE),unsigned(dut.P_MANUFACTURING),unsigned(dut.P_DEBUG),unsigned(dut.P_FUNCTIONAL_RESET),unsigned(dut.P_POWER),unsigned(dut.P_ISOLATION));
  auto shifted=[&](unsigned old,unsigned serial){unsigned next=serial<<SCAN_BITS[0];for(unsigned i=1;i<WIDTH;++i)next|=((old>>SCAN_BITS[i-1])&1u)<<SCAN_BITS[i];return next;};
  auto sample=[&](const char*phase,unsigned serial,bool capture,bool unload){
   dut.P_FCLK=0;dut.P_TCLK=0;dut.P_SHIFT_REQUEST=capture?(f[6]?0:1):1;dut.P_SERIAL_IN=serial;eval();
   const unsigned pre_serial=dut.P_SERIAL_OUT,want_serial=(ideal>>SCAN_BITS[WIDTH-1])&1u;
   ideal=(f[7] && f[1])?(capture?CAPTURE_WORD:shifted(ideal,serial)):0;
   if(f[5])dut.P_TCLK=1;else dut.P_FCLK=1;eval();++checks;failures+=unsigned(dut.P_RAW_STATE)!=ideal;
   if(unload){++checks;failures+=pre_serial!=want_serial;}
   ++step;std::printf("STEP %u %s %u %u %u %u %u %u %u %u %u %u %u %u %u\n",step,phase,unsigned(dut.P_SERIAL_IN),unsigned(dut.P_PARALLEL_DATA),unsigned(dut.P_TCLK),unsigned(dut.P_FCLK),unsigned(dut.P_RESET_LEVEL),unsigned(dut.P_SCAN_ENABLE),unsigned(dut.P_CHAIN_CLOCK),pre_serial,unsigned(dut.P_RAW_STATE),unsigned(dut.P_VISIBLE_STATE),ideal,want_serial,failures);
   dut.P_FCLK=0;dut.P_TCLK=0;eval();
  };
  for(unsigned i=0;i<WIDTH;++i)sample("shift",(LOAD_WORD>>SCAN_BITS[WIDTH-1-i])&1u,false,false);
  sample("capture",0,true,false);
  for(unsigned i=0;i<WIDTH;++i)sample("unload",0,false,true);
  dut.final();std::printf("NATIVE_RESULT %u %u %u\n",step,checks,failures);return failures?1:0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 2;}
}
