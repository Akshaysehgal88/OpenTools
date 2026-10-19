#ifndef OPENTOOLS_EXAMPLE_DESCRIPTOR_H
#define OPENTOOLS_EXAMPLE_DESCRIPTOR_H
#include <stdint.h>
enum opcode_encoding { OP_READ = 1, OP_WRITE = 2 };
struct descriptor {
    uint64_t address;
    uint32_t length;
    uint32_t opcode;
    uint32_t reserved;
    uint32_t padding;
};
#endif
