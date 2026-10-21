#pragma once
#include <cstdio>
#include <map>
#include <string>
struct ObservationChecker {
    std::string policy;
    std::map<unsigned,unsigned> expected;
    unsigned checked=0, failures=0;
    explicit ObservationChecker(std::string selected):policy(selected){}
    bool enabled(bool mode)const{return policy!="disabled" && !(policy=="mode0" && mode);}
    void emit(unsigned tick,unsigned id,unsigned want,unsigned observed) {
        ++checked;const bool ok=want==observed;if(!ok)++failures;
        std::printf("CHECK %u %u %u %u %u\n",tick,id,want,observed,unsigned(ok));
    }
    void sample(unsigned tick,bool reset,bool mode,bool enabled,bool valid,bool ready,unsigned id,unsigned data,
                bool done,bool take,unsigned done_id,unsigned observed) {
        if(reset){expected.clear();return;}
        if(policy=="stimulus") {
            if(enabled && valid)emit(tick,id,data,data); // Deliberately wrong observation point.
        } else if(done && take && enabled) {
            const auto found=expected.find(done_id);const unsigned want=found==expected.end()?65535:found->second;
            emit(tick,policy=="wrong-id"?(done_id^1u):done_id,want,observed);
        }
        if(done && take)expected.erase(done_id);
        if(valid && ready)expected[id]=data^NATIVE_XOR;
    }
};
