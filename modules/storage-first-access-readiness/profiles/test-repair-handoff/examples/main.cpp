#include "Vtop.h"
#include "verilated.h"
#include "plans.hpp"
#include <iostream>
#include <vector>
int main(int argc,char**argv){
 if(argc!=2)return 3;unsigned selection=0;
 for(const char*p=argv[1];*p;++p){if(*p<'0'||*p>'9')return 3;selection=selection*10+(*p-'0');}
 if(selection>=sizeof(PLANS)/sizeof(PLANS[0]))return 3;
 const Plan& p=PLANS[selection];VerilatedContext context;Vtop d{&context};unsigned seq=0,checks=0,failures=0;
 d.P_CLK=0;d.P_RESET=!RESET_ASSERTED;d.P_VALID=0;d.P_CFG=p.cfg;d.P_OPERATION=0;d.P_WORD_ADDRESS=0;d.P_PHYSICAL_ADDRESS=0;d.P_REPAIR_INPUT=p.expected_payload;d.P_WRITE_DATA=0;d.P_BYTE_ENABLE=15;d.P_RAW_INPUT=0;d.eval();d.P_RESET=RESET_ASSERTED;d.eval();d.P_RESET=!RESET_ASSERTED;d.eval();
 std::cout<<"TIME_UNITS "<<context.timeunit()<<' '<<context.timeprecision()<<"\nCONFIG "<<selection<<' '<<p.cfg<<' '<<WORDS<<' '<<PHYSICAL<<" 32 39 4 12 "<<RESET_ASSERTED<<' '<<p.expected_payload<<' '<<p.repair_required<<' '<<p.count<<'\n';
 if(context.timeunit()!=-9||context.timeprecision()!=-9)return 3;
 auto state=[&](){return std::vector<uint64_t>{d.P_TEST_OWNER,d.P_TEST_DONE,d.P_REPAIR_LOADED,d.P_REPAIR_ACTIVE,d.P_ECC_ENABLED,d.P_INITIALIZED,d.P_RELEASED,d.P_REPAIR_EPOCH,d.P_LOADED_PAYLOAD,d.P_DECODED_BAD,d.P_DECODED_SPARE,d.P_CANONICAL_BAD,d.P_CANONICAL_SPARE,d.P_TEST_WRITES,d.P_TEST_READS};};
 std::cout<<"INIT";for(auto value:state())std::cout<<' '<<value;std::cout<<'\n';
 auto check=[&](bool value){++checks;failures+=!value;};
 const unsigned wanted_bad=(p.expected_payload>>6)&15,wanted_spare=(p.expected_payload>>1)&15;
 for(unsigned index=0;index<p.count;++index){
  const Step&s=p.steps[index];auto before=state();bool prerequisites=d.P_TEST_DONE&&d.P_REPAIR_LOADED&&d.P_ECC_ENABLED&&d.P_INITIALIZED==((1u<<WORDS)-1);
  d.P_CLK=0;d.P_VALID=1;d.P_OPERATION=s.operation;d.P_WORD_ADDRESS=s.word;d.P_PHYSICAL_ADDRESS=s.physical;d.P_REPAIR_INPUT=s.repair_input;d.P_WRITE_DATA=s.write_data;d.P_BYTE_ENABLE=s.byte_enable;d.P_RAW_INPUT=s.raw_input;d.eval();context.timeInc(1);d.P_CLK=1;d.eval();context.timeInc(1);++seq;
  check(bool(d.P_ACCEPTED)==s.expect_accept);
  unsigned target=p.repair_required && s.word==wanted_bad?wanted_spare:s.word;
  if(!s.expect_accept)check(!d.P_COMMITTED&&!d.P_ADDRESS_VALID);
  else if(s.operation==1)check(d.P_BEFORE_CODEWORD==s.raw_input);
  else if(s.operation==2)check(d.P_TEST_DONE);
  else if(s.operation==3)check(d.P_REPAIR_LOADED && bool(d.P_REPAIR_ACTIVE)==p.repair_required && d.P_LOADED_PAYLOAD==p.expected_payload && (!p.repair_required || (d.P_DECODED_BAD==wanted_bad&&d.P_DECODED_SPARE==wanted_spare)));
  else if(s.operation==4)check(d.P_ECC_ENABLED);
  else if(s.operation==5)check(d.P_COMMITTED&&d.P_ACTUAL_PHYSICAL==target&&d.P_AFTER_CODEWORD==s.expected_after);
  else if(s.operation==6)check(s.expect_release==0?!d.P_RELEASED&&d.P_TEST_OWNER:d.P_RELEASED&&prerequisites);
  else if(s.operation==7)check(!d.P_ERROR&&d.P_READ_DATA==s.expected_data&&d.P_ACTUAL_PHYSICAL==target&&d.P_ECC_ENABLED);
  else if(s.operation==8){
   if(s.byte_enable==0)check(!d.P_COMMITTED&&!d.P_INTERNAL_READ&&!d.P_ERROR&&d.P_AFTER_CODEWORD==d.P_BEFORE_CODEWORD);
   else check(d.P_COMMITTED&&!d.P_ERROR&&d.P_ACTUAL_PHYSICAL==target&&d.P_AFTER_CODEWORD==s.expected_after&&bool(d.P_INTERNAL_READ)==(s.byte_enable!=15));
  }else if(s.operation==10)check(!d.P_ECC_ENABLED);
  std::vector<uint64_t> values=before;
  values.insert(values.end(),{d.P_OPERATION,d.P_WORD_ADDRESS,d.P_PHYSICAL_ADDRESS,d.P_REPAIR_INPUT,d.P_WRITE_DATA,d.P_BYTE_ENABLE,d.P_RAW_INPUT});
  values.insert(values.end(),{d.P_ACCEPTED,d.P_ADDRESS_VALID,d.P_COMMITTED,d.P_ERROR,d.P_INTERNAL_READ,d.P_CORRECTABLE,d.P_UNCORRECTABLE,d.P_TEST_OWNER,d.P_TEST_DONE,d.P_REPAIR_LOADED,d.P_REPAIR_ACTIVE,d.P_ECC_ENABLED,d.P_RELEASED,d.P_INITIALIZED,d.P_DECODED_BAD,d.P_DECODED_SPARE,d.P_CANONICAL_BAD,d.P_CANONICAL_SPARE,d.P_REPAIR_EPOCH,d.P_LOADED_PAYLOAD,d.P_ACTUAL_PHYSICAL,d.P_BEFORE_CODEWORD,d.P_AFTER_CODEWORD,d.P_READ_DATA,d.P_OLD_DATA,d.P_TEST_WRITES,d.P_TEST_READS,checks,failures});
  std::cout<<"TX "<<seq<<' '<<context.time()<<' '<<s.id;for(auto value:values)std::cout<<' '<<value;std::cout<<'\n';
  d.P_CLK=0;d.P_VALID=0;d.eval();context.timeInc(1);
 }
 std::cout<<"NATIVE_RESULT "<<seq<<' '<<checks<<' '<<failures<<'\n';d.final();return failures?1:0;
}
