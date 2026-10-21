#ifndef OPENTOOLS_CONFIGURATION_H
#define OPENTOOLS_CONFIGURATION_H
#include <stdint.h>
#include "selected_config.h"
#include "defaults.h"
/* Scalar ABI anchor for the existing probe; constants are measured separately. */
struct configuration_probe { uint64_t anchor; };
static unsigned char configuration_storage[DEPTH][WORD_BYTES];
static long long consumed_word_bytes(void) { return sizeof(configuration_storage[0]); }
static long long consumed_depth(void) { return sizeof(configuration_storage)/sizeof(configuration_storage[0]); }
static long long consumed_feature(void) { return FEATURE; }
static long long consumed_mode(void) { return MODE; }
#endif
