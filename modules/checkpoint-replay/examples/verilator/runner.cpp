// A bounded save/restore recipe, not a process or general testbench checkpoint.
#include "Vtop.h"
#include "verilated.h"
#include "verilated_save.h"

#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

#ifndef PROFILE_BUILD_REV
#define PROFILE_BUILD_REV 1
#endif

using Clock = std::chrono::steady_clock;
static uint64_t elapsed(Clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
}
static uint64_t number(const char* text) {
    std::string value(text);
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("unsigned decimal arguments required");
    return std::stoull(value);
}
struct Pending { uint64_t sequence, due; uint8_t expected; };
struct Driver {
    uint64_t step = 0;
    uint32_t rng = 0;
    std::array<uint8_t, 16> memory{};
    std::deque<Pending> pending;
    uint64_t digest = 0, checked = 0, failures = 0;
};

static std::array<uint8_t, 16> image(const std::string& path) {
    std::ifstream stream(path, std::ios::binary);
    std::array<uint8_t, 16> data{};
    if (!stream.read(reinterpret_cast<char*>(data.data()), data.size()) || stream.peek() != EOF)
        throw std::runtime_error("prefix image must contain exactly 16 bytes");
    return data;
}

static void tick(Vtop& model, VerilatedContext& context) {
    model.clk=0; model.eval(); context.timeInc(1);
    model.clk=1; model.eval(); context.timeInc(1);
    model.clk=0; model.eval();
}

static void advance(Vtop& model, VerilatedContext& context, Driver& driver,
                    const std::array<uint8_t, 16>& firmware) {
    ++driver.step;
    driver.rng=driver.rng*1664525u+1013904223u;
    const unsigned address=driver.step<=16 ? driver.step-1 : (driver.rng>>24)&15u;
    const uint8_t data=driver.step<=16 ? firmware[address] : (driver.rng>>16)&255u;
    const bool write=driver.step<=16 || (driver.rng&1u);
    driver.pending.push_back({driver.step, driver.step+1, driver.memory[address]});
    model.addr=address; model.data_in=data; model.write_enable=write;
    tick(model,context);
    if (!driver.pending.empty() && driver.pending.front().due==driver.step) {
        const auto expected=driver.pending.front();
        driver.pending.pop_front();
        ++driver.checked;
        if (!model.valid || model.data_out!=expected.expected) ++driver.failures;
        driver.digest=driver.digest*131u+model.data_out+expected.sequence;
    } else if (model.valid) {
        ++driver.failures;
    }
    if (write) driver.memory[address]=data;
}

static void bytes(const std::array<uint8_t,16>& values) {
    std::printf("[");
    for (unsigned i=0;i<values.size();++i) std::printf("%s%u",i?",":"",unsigned(values[i]));
    std::printf("]");
}

static void observation(const char* kind, Vtop& model, VerilatedContext& context, const Driver& driver) {
    std::array<uint8_t,16> memory{};
    for (unsigned i=0;i<memory.size();++i) {
        model.probe_addr=i; model.eval(); memory[i]=model.probe_data;
    }
    std::printf("{\"type\":\"%s\",\"step\":%llu,\"values\":{\"time\":%llu,\"rng\":%u,\"dut_memory\":",
                kind,(unsigned long long)driver.step,(unsigned long long)context.time(),driver.rng);
    bytes(memory);
    std::printf(",\"reference_memory\":"); bytes(driver.memory);
    std::printf(",\"pending\":[");
    bool first=true;
    for (const auto& value:driver.pending) {
        std::printf("%s[%llu,%llu,%u]",first?"":",",(unsigned long long)value.sequence,
                    (unsigned long long)value.due,unsigned(value.expected));
        first=false;
    }
    std::printf("],\"checker_digest\":\"%016llx\",\"checked\":%llu,\"failures\":%llu,\"valid\":%u,\"data_out\":%u}}\n",
                (unsigned long long)driver.digest,(unsigned long long)driver.checked,
                (unsigned long long)driver.failures,unsigned(model.valid),unsigned(model.data_out));
}

static void save(const std::string& path, Vtop& model, const Driver& driver,
                 const std::array<uint8_t,16>& firmware, uint32_t seed, uint64_t prefix, bool save_rng) {
    if (std::filesystem::exists(path)) throw std::runtime_error("checkpoint output must be new");
    VerilatedSave stream;
    stream.open(path);
    if (!stream.isOpen()) throw std::runtime_error("cannot open checkpoint output");
    const uint64_t magic=0x4f5452504c415931ULL;
    const uint32_t revision=PROFILE_BUILD_REV, rng_present=save_rng?1:0;
    stream << magic << revision << seed << prefix << rng_present << driver.step;
    for (const auto value:firmware) stream << value;
    if (save_rng) stream << driver.rng;
    for (const auto value:driver.memory) stream << value;
    stream << driver.digest << driver.checked << driver.failures;
    const uint32_t pending=driver.pending.size();
    stream << pending;
    for (const auto& value:driver.pending) stream << value.sequence << value.due << value.expected;
    stream << model; // Generated 5.020 model includes its serialized context/time.
    stream.close();
}

static bool restore(const std::string& path, Vtop& model, Driver& driver,
                    const std::array<uint8_t,16>& firmware, uint32_t seed, uint64_t prefix) {
    VerilatedRestore stream;
    stream.open(path);
    if (!stream.isOpen()) throw std::runtime_error("cannot open checkpoint input");
    uint64_t magic=0, saved_prefix=0;
    uint32_t revision=0, saved_seed=0, rng_present=0;
    stream >> magic >> revision >> saved_seed >> saved_prefix >> rng_present >> driver.step;
    if (magic!=0x4f5452504c415931ULL || revision!=PROFILE_BUILD_REV || rng_present>1)
        throw std::runtime_error("unsupported example checkpoint recipe");
    if (saved_seed!=seed || saved_prefix!=prefix || driver.step!=prefix)
        throw std::runtime_error("incompatible prefix seed or capture step");
    for (const auto expected:firmware) {
        uint8_t actual=0; stream >> actual;
        if (actual!=expected) throw std::runtime_error("incompatible prefix image bytes");
    }
    if (rng_present) stream >> driver.rng;
    for (auto& value:driver.memory) stream >> value;
    stream >> driver.digest >> driver.checked >> driver.failures;
    uint32_t pending=0;
    stream >> pending;
    if (pending>16) throw std::runtime_error("invalid pending queue length");
    for (uint32_t i=0;i<pending;++i) {
        Pending value{};
        stream >> value.sequence >> value.due >> value.expected;
        driver.pending.push_back(value);
    }
    stream >> model;
    stream.close();
    return rng_present;
}

int main(int argc, char** argv) {
    try {
        if (argc!=9) throw std::runtime_error("mode checkpoint image seed prefix suffix save_rng sample_every_step required");
        const std::string mode=argv[1], checkpoint=argv[2];
        if (mode!="control" && mode!="restart" && mode!="restore" && mode!="restore-drop-queue")
            throw std::runtime_error("unsupported example mode");
        const auto firmware=image(argv[3]);
        const auto seed_value=number(argv[4]), prefix=number(argv[5]), suffix=number(argv[6]);
        const auto save_rng=number(argv[7]);
        const auto sample_every_step=number(argv[8]);
        if (seed_value>0xffffffffULL || prefix<16 || suffix==0 || prefix>10000000 || suffix>10000000
            || prefix+suffix>10000000 || save_rng>1 || sample_every_step>1)
            throw std::runtime_error("example argument outside supported bounds");
        VerilatedContext context;
        context.threads(1);
        Vtop model(&context);
        Driver driver;
        driver.rng=seed_value;
        uint64_t prefix_ns=0, save_ns=0, restore_ns=0;
        bool rng_present=save_rng;
        if (mode=="control" || mode=="restart") {
            auto start=Clock::now();
            model.reset_n=0; tick(model,context); tick(model,context); model.reset_n=1;
            for (uint64_t i=0;i<prefix;++i) advance(model,context,driver,firmware);
            prefix_ns=elapsed(start);
            if (mode=="control") {
                start=Clock::now();
                save(checkpoint,model,driver,firmware,seed_value,prefix,save_rng);
                save_ns=elapsed(start);
            }
        } else {
            auto start=Clock::now();
            rng_present=restore(checkpoint,model,driver,firmware,seed_value,prefix);
            restore_ns=elapsed(start);
            if (mode=="restore-drop-queue") driver.pending.clear();
        }
        observation("start",model,context,driver);
        auto start=Clock::now();
        for (uint64_t i=0;i<suffix;++i) {
            advance(model,context,driver,firmware);
            if (sample_every_step) observation("sample",model,context,driver);
        }
        const auto suffix_ns=elapsed(start);
        observation("end",model,context,driver);
        model.final();
        std::printf("{\"type\":\"summary\",\"failures\":%llu,\"rng_captured\":%s,\"sample_every_step\":%s,\"prefix_ns\":%llu,\"save_ns\":%llu,\"restore_ns\":%llu,\"suffix_ns\":%llu}\n",
                    (unsigned long long)driver.failures,mode=="restart"?"null":rng_present?"true":"false",sample_every_step?"true":"false",(unsigned long long)prefix_ns,
                    (unsigned long long)save_ns,(unsigned long long)restore_ns,(unsigned long long)suffix_ns);
        return driver.failures ? 1 : 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr,"example error: %s\n",error.what());
        return 3;
    }
}
