// Qualified scheduled-window VCD hooks for this example, not a universal CLI.
#include "Vtop.h"
#include "verilated.h"
#if VM_TRACE_VCD
#include "verilated_vcd_c.h"
#endif
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

static uint64_t number(const std::string& value) {
    if (value.empty() || value.find_first_not_of("0123456789")!=std::string::npos)
        throw std::runtime_error("unsigned decimal tick/cycle arguments required");
    return std::stoull(value);
}
struct Options {
    std::string file;
    uint64_t start=0,end=260,stop=260,request=90,config=60,config_value=1;
    std::vector<std::string> selectors;
    bool inventory=false,capture=false;
};
static Options options(int argc,char** argv) {
    Options out;
    if (argc==3 && std::string(argv[1])=="--inventory-vcd") {
        out.inventory=true;out.capture=true;out.file=argv[2];return out;
    }
    std::set<std::string> seen;
    bool workload=false;
    for (int i=1;i<argc;++i) {
        std::string key=argv[i];
        if (key=="--") {
            if (workload) throw std::runtime_error("repeated workload delimiter");
            workload=true;continue;
        }
        if (key=="--no-capture" && !workload) {
            if (!seen.insert(key).second) throw std::runtime_error("duplicate option");
            continue;
        }
        if (i+1>=argc) throw std::runtime_error("option value required");
        const std::string value=argv[++i];
        if (key!="--select" && !seen.insert(key).second) throw std::runtime_error("duplicate option");
        if (!workload) {
            if (key=="--capture-vcd") {out.file=value;out.capture=true;}
            else if (key=="--start-tick") out.start=number(value);
            else if (key=="--end-tick") out.end=number(value);
            else if (key=="--stop-tick") out.stop=number(value);
            else if (key=="--select") out.selectors.push_back(value);
            else throw std::runtime_error("unsupported trace option");
        } else {
            if (key=="--request-cycle") out.request=number(value);
            else if (key=="--config-cycle") out.config=number(value);
            else if (key=="--config-value") out.config_value=number(value);
            else throw std::runtime_error("unsupported workload option");
        }
    }
    if (out.capture && seen.count("--no-capture")) throw std::runtime_error("choose capture or no-capture");
    if (!out.capture && !seen.count("--no-capture")) throw std::runtime_error("explicit capture mode required");
    if (out.capture && (out.selectors.empty() || !seen.count("--start-tick") || !seen.count("--end-tick")))
        throw std::runtime_error("explicit nonempty selection and window required");
    if (!seen.count("--stop-tick") || out.stop>1000000 || out.capture && (out.end>out.stop || out.start>out.end)
        || out.request==0 || out.config==0 || out.request>500000 || out.config>500000 || out.config_value>1)
        throw std::runtime_error("unsupported example run bounds");
    return out;
}

int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string(argv[1])=="--capabilities") {
            std::printf("{\"profile\":\"verilator-5.020-vcd-wrapper.v1\",\"producer_version\":\"%s\",\"trace_compiled\":%s,\"waveform_format\":\"vcd\",\"tick\":{\"value\":\"1\",\"unit\":\"ns\"},\"max_tick\":1000000,\"selection\":\"dumpvars(1,leaf) before open\"}\n",
                        Verilated::productVersion(),VM_TRACE_VCD?"true":"false");
            return 0;
        }
        const Options opts=options(argc,argv);
        if (opts.capture && (opts.file.empty() || opts.file=="-" || std::filesystem::exists(opts.file)))
            throw std::runtime_error("choose a new waveform file");
#if !VM_TRACE_VCD
        if (opts.capture) throw std::runtime_error("this binary lacks VCD instrumentation");
#endif
        VerilatedContext context;
        context.threads(1);
        context.traceEverOn(VM_TRACE_VCD);
        Vtop model(&context);
#if VM_TRACE_VCD
        std::unique_ptr<VerilatedVcdC> trace;
        bool opened=false;
        if (opts.capture) {
            trace=std::make_unique<VerilatedVcdC>();
            model.trace(trace.get(),99);
            for (const auto& name:opts.selectors) trace->dumpvars(1,name);
        }
#endif
        if (opts.inventory) {
            model.eval();
#if VM_TRACE_VCD
            trace->open(opts.file.c_str());trace->dump(0);trace->close();
#endif
            std::printf("{\"type\":\"inventory\",\"tick\":0}\n");
            return 0;
        }
        for (uint64_t tick=0;tick<=opts.stop;++tick) {
            context.time(tick);
            model.clk=tick>0 && tick%2==0;
            model.reset_n=tick>=6;
            model.request_valid=tick>=2*opts.request && tick<2*opts.request+2;
            model.config_write=tick>=2*opts.config && tick<2*opts.config+2;
            model.config_value=opts.config_value;
            model.eval();
#if VM_TRACE_VCD
            if (trace && tick>=opts.start && tick<=opts.end) {
                if (!opened) {trace->open(opts.file.c_str());opened=true;}
                trace->dump(context.time());
            }
#endif
            std::printf("{\"tick\":%llu,\"clk\":%u,\"reset_n\":%u,\"request_valid\":%u,\"accepted\":%u,\"outstanding\":%u,\"response\":%u,\"timeout\":%u,\"grant\":%u,\"quiesce\":%u,\"age\":%u}\n",
                        (unsigned long long)tick,unsigned(model.clk),unsigned(model.reset_n),unsigned(model.request_valid),
                        unsigned(model.accepted),unsigned(model.outstanding),unsigned(model.response),unsigned(model.timeout),
                        unsigned(model.grant),unsigned(model.quiesce_active),unsigned(model.age));
        }
#if VM_TRACE_VCD
        if (trace && opened) trace->close();
#endif
        model.final();
        return 0; // A simulated timeout is an observation, not a failed wrapper invocation.
    } catch (const std::exception& error) {
        std::fprintf(stderr,"capture example error: %s\n",error.what());
        return 3;
    }
}
