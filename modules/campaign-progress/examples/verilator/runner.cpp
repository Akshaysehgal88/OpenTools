#include "Vtop.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <string>

unsigned number(const char* value) {
    const std::string raw=value;
    if(raw.empty() || raw.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("unsigned integer required");
    const unsigned long long result=std::stoull(raw);
    if(result>std::numeric_limits<unsigned>::max()) throw std::runtime_error("integer does not fit native counter");
    return unsigned(result);
}

int main(int argc,char** argv) {
    try {
        if(argc!=8) throw std::runtime_error("use RUN CYCLES ACTIVE CONFIG VALUES BINS FORCE_FAILURE");
        const std::string ref=argv[1];
        if(ref.empty() || ref.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")!=std::string::npos)
            throw std::runtime_error("simple run reference required");
        const unsigned cycles=number(argv[2]),active=number(argv[3]),config=number(argv[4]),values=number(argv[5]),bins=number(argv[6]),force=number(argv[7]);
        if(!cycles || active>1 || config>1 || force>1 || (values!=3 && values!=4) || (bins!=3 && bins!=4)) throw std::runtime_error("unsupported fixture argument");
        VerilatedContext context;Vtop model{&context};unsigned checks=0,failures=0,mask=0;
        auto check=[&](bool good){++checks;if(!good)++failures;};
        auto eval=[&](){model.eval();context.timeInc(1);};
        auto cycle=[&](){model.clk=0;eval();model.clk=1;eval();model.clk=0;eval();};
        model.clk=0;model.reset_n=0;model.valid=0;model.active=active;model.config_bit=config;model.payload=0;cycle();
        model.reset_n=1;model.valid=1;
        for(unsigned i=0;i<cycles;++i) {
            const unsigned value=i%values;model.payload=value;cycle();
            check(model.accepted_count==(active?i+1:0));
            if(active){check(model.echo==(value^config));mask|=1u<<(value%bins);}
        }
        if(force) check(false);
        model.final();
        std::printf("{\"run_ref\":\"%s\",\"config\":%u,\"stimulus_cycles\":%u,\"active\":%s,\"values\":%u,\"bin_count\":%u,\"hit_mask\":%u,\"accepted\":%u,\"checks\":%u,\"failures\":%u,\"passed\":%s,\"simulated_ticks\":%llu}\n",
            ref.c_str(),config,cycles,active?"true":"false",values,bins,mask,unsigned(model.accepted_count),checks,failures,failures?"false":"true",(unsigned long long)context.time());
        return failures?1:0;
    }catch(const std::exception& error){std::fprintf(stderr,"%s\n",error.what());return 2;}
}
