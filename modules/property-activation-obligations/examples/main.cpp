#include "Vtop.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <cstring>
#include <iostream>
#include <memory>

int main(int argc, char** argv) {
    const bool clean = argc > 1 && std::strcmp(argv[1], "clean") == 0;
    auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
    if (argc > 2 && std::strcmp(argv[2], "off") == 0) context->assertOn(false);
    context->coveragep()->forcePerInstance(true);
    auto model = std::make_unique<Vtop>(context.get());
    constexpr int cycles = 8;
    for (int cycle = 0; cycle < cycles; ++cycle) {
        model->aon_clk = 0; model->functional_clk = 0;
        model->reset = cycle == 0;
        model->mode = cycle >= 3 && cycle <= 5;
        model->event_req = cycle == 2 || cycle == 4;
        model->condition_ok = clean || cycle != 4;
        model->eval(); context->timeInc(1);
        model->aon_clk = 1;
        model->functional_clk = model->mode ? 0 : 1;
        std::cout << "DRIVE " << context->time() << " 1 "
                  << int(model->functional_clk) << " " << int(model->reset) << " "
                  << int(model->mode) << " " << int(model->event_req) << " "
                  << int(model->condition_ok) << " " << int(context->assertOn()) << "\n";
        model->eval(); context->timeInc(1);
        model->aon_clk = 0; model->functional_clk = 0; model->eval();
    }
    model->final();
    context->coveragep()->write("coverage.dat");
    std::cout << "RUN_END " << context->time() << " " << cycles << "\n";
    return 0;
}
