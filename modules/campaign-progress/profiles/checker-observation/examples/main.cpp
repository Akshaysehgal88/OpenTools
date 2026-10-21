#include "Vtop.h"
#include "verilated.h"
#include "ports.hpp"
#include "checker.hpp"
#include <cstdio>
#include <stdexcept>
#include <string>
int main(int argc,char**argv) {
    try {
        if(argc!=4)throw std::runtime_error("use POLICY SCENARIO clean|fault");
        const std::string policy=argv[1],scenario=argv[2],fault=argv[3];
        if(policy!="good" && policy!="mode0" && policy!="disabled" && policy!="stimulus" && policy!="wrong-id")throw std::runtime_error("unknown checker policy");
        if(scenario!="normal" && scenario!="reset" && scenario!="stalled" && scenario!="short" && scenario!="no-mode1")throw std::runtime_error("unknown scenario");
        if(fault!="clean" && fault!="fault")throw std::runtime_error("unknown fault selection");
        VerilatedContext context;Vtop model{&context};ObservationChecker checker(policy);
        unsigned stimulus=0,accepted=0,completed=0,next_id=1;
        const unsigned cycles=scenario=="short"?11:32;
        auto eval=[&](){model.eval();context.timeInc(1);};
        model.M_CLOCK=0;
        for(unsigned tick=0;tick<cycles;++tick) {
            const bool reset=tick<2 || (scenario=="reset" && tick==9);
            const bool mode=scenario!="no-mode1" && tick>=16;
            const bool enabled=checker.enabled(mode);
            model.M_CLOCK=0;model.M_RESET=reset?RESET_ACTIVE:!RESET_ACTIVE;
            model.M_MODE=mode;model.M_FAULT=fault=="fault";
            model.M_REQ_VALID=tick>=2 && tick<24;model.M_RSP_READY=scenario!="stalled" && tick%4!=0;
            model.M_REQ_ID=next_id;model.M_REQ_DATA=(next_id*3u+7u)&65535u;eval();
            // Independent raw pre-edge top-port sample; no checker policy gates this journal.
            const unsigned rv=model.M_REQ_VALID,rr=model.M_REQ_READY,ri=model.M_REQ_ID,rd=model.M_REQ_DATA;
            const unsigned sv=model.M_RSP_VALID,sr=model.M_RSP_READY,si=model.M_RSP_ID,sd=model.M_RSP_DATA;
            std::printf("EDGE %u %u %u %u %u %u %u %u %u %u %u %u %u\n",tick,unsigned(model.M_RESET),unsigned(model.M_MODE),unsigned(enabled),rv,rr,ri,rd,sv,sr,si,sd,unsigned(model.M_CLOCK));
            if(!reset){stimulus+=rv;accepted+=rv&&rr;completed+=sv&&sr;}
            checker.sample(tick,reset,mode,enabled,rv,rr,ri,rd,sv,sr,si,sd);
            if(!reset && rv && rr)++next_id;
            model.M_CLOCK=1;eval();model.M_CLOCK=0;eval();
        }
        model.final();
        std::printf("FINAL %u %u %u %u %u\n",stimulus,accepted,completed,checker.checked,checker.failures);
        return checker.failures?1:0;
    }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 2;}
}
