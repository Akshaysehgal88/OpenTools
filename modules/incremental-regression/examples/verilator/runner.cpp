#include "Vtop.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>

int main(int argc,char** argv) {
    try {
        if (argc!=3) throw std::runtime_error("use TEST CONFIG(0|1)");
        const std::string test=argv[1],config=argv[2];
        if (config!="0" && config!="1") throw std::runtime_error("configuration must be 0 or 1");
        if (test!="soc_smoke" && test!="dma_directed" && test!="fabric_integration" &&
            test!="soc_stress" && test!="reset_sequence" && test!="fabric_long")
            throw std::runtime_error("unknown test; no inferred aliases");
        VerilatedContext context;Vtop model{&context};
        unsigned checks=0,failures=0;
        auto check=[&](bool condition){++checks;if(!condition)++failures;};
        auto eval=[&](){model.eval();context.timeInc(1);};
        auto cycle=[&](){model.clk=0;eval();model.clk=1;eval();model.clk=0;eval();};
        model.alternate=config=="1";model.data=0;model.reset_n=0;model.clk=0;cycle();
        check(model.alive==0 && model.dma_value==0 && model.fabric_value==0);
        model.reset_n=1;cycle();check(model.alive==1);
        if(test=="dma_directed" || test=="fabric_integration") {
            model.data=17;eval();check(model.dma_value==17);
            if(test=="fabric_integration") {check(model.fabric_value==18);check(model.integrated_value==(17^18));}
        } else if(test=="soc_stress" || test=="fabric_long") {
            const unsigned count=test=="soc_stress"?256:4096;
            for(unsigned i=0;i<count;++i) {
                const uint8_t value=uint8_t(i*73+19);model.data=value;cycle();
                const uint8_t expected=uint8_t(value+1);check(model.fabric_value==expected);
                if(test=="soc_stress") {check(model.dma_value==value);check(model.integrated_value==(value^expected));}
            }
        } else if(test=="reset_sequence") {
            for(unsigned i=0;i<8;++i) {model.reset_n=i%2;cycle();check(model.alive==(i%2));}
        }
        model.final();
        std::printf("{\"test\":\"%s\",\"config\":%s,\"checks\":%u,\"failures\":%u,\"passed\":%s}\n",
                    test.c_str(),config.c_str(),checks,failures,failures?"false":"true");
        return failures?1:0;
    } catch(const std::exception& error) {std::fprintf(stderr,"%s\n",error.what());return 2;}
}
