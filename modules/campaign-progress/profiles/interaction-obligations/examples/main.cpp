#include "Vtop.h"
#include "verilated.h"
#include "ports.hpp"
#include <cstdio>
#include <stdexcept>
#include <string>

int main(int argc,char**argv) {
  try {
    if(argc!=5)throw std::runtime_error("use SCENARIO good|bug warm|cold on|off");
    const std::string scenario=argv[1],variant=argv[2],mode=argv[3],checkers=argv[4];
    if(scenario!="separate" && scenario!="arrive" && scenario!="pending" && scenario!="ack-arrive" && scenario!="portfolio" && scenario!="short")throw std::runtime_error("unknown scenario");
    if((variant!="good" && variant!="bug") || (mode!="warm" && mode!="cold") || (checkers!="on" && checkers!="off"))throw std::runtime_error("unknown selection");
    VerilatedContext context;Vtop dut{&context};bool expected=false;unsigned count=0,failures=0;
    auto evaluate=[&](){dut.eval();context.timeInc(1);};
    const unsigned cycles=scenario=="short"?5:32;
    for(unsigned tick=0;tick<cycles;++tick) {
      const bool reset=tick<2,retain=mode=="warm",enabled=checkers=="on";
      bool hold=false,event=false,ack=false;
      if(scenario=="separate"){hold=tick>=2 && tick<=4;event=tick==10;ack=tick==12;}
      else if(scenario=="arrive" || scenario=="short"){hold=tick>=2 && tick<=4;event=tick==3;ack=tick==8;}
      else if(scenario=="pending"){hold=tick>=3 && tick<=5;event=tick==2;ack=tick==9;}
      else if(scenario=="ack-arrive"){event=tick==2 || tick==4;ack=tick==4 || tick==8;}
      else {hold=(tick>=2 && tick<=4) || (tick>=11 && tick<=13);event=tick==3 || tick==10 || tick==19 || tick==21;ack=tick==7 || tick==16 || tick==21 || tick==25;}
      dut.M_CLOCK=0;dut.M_RESET=reset?RESET_ACTIVE:!RESET_ACTIVE;dut.M_HOLD=hold;dut.M_RETAIN=retain;dut.M_EVENT=event;dut.M_ACK=ack;
      dut.M_DROP=variant=="bug";dut.M_ACK_PRIORITY=variant=="bug";evaluate();
      const unsigned before=dut.M_PENDING,visible=dut.M_VISIBLE,clock_before=dut.M_CLOCK;
      // Independent expected-state checker; the raw sample is never gated by it.
      if(reset || (hold && !retain))expected=false;
      else if(event)expected=true;
      else if(ack && !hold)expected=false;
      dut.M_CLOCK=1;evaluate();
      std::printf("FRAME %u %u %u %u %u %u %u %u %u %u %u %u %u\n",tick,unsigned(dut.M_RESET),unsigned(dut.M_HOLD),unsigned(dut.M_EVENT),unsigned(dut.M_ACK),unsigned(dut.M_RETAIN),before,visible,unsigned(dut.M_PENDING),unsigned(dut.M_VISIBLE),unsigned(enabled),clock_before,unsigned(dut.M_CLOCK));
      auto compare=[&](const char*id,bool want,bool actual){if(enabled){++count;const bool ok=want==actual;failures+=!ok;std::printf("CHECK %u %s %u %u %u\n",tick,id,unsigned(want),unsigned(actual),unsigned(ok));}};
      compare("state_model",expected,dut.M_PENDING);compare("delivery_model",expected && !hold,dut.M_VISIBLE);
      dut.M_CLOCK=0;evaluate();
    }
    dut.final();std::printf("RESULT %u %u %u\n",cycles,count,failures);return failures?1:0;
  }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 2;}
}
