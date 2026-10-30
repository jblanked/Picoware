#pragma once

// Upstream mJS engine C++ sources include the Unix delay API indirectly.
// Declare it with C linkage before those headers, without changing firmware.
extern "C" {
#include "py/mphal.h"
}
