#pragma once

#include <stdbool.h>
#include <stdint.h>

#define POOM_INPUT_A 0
#define POOM_INPUT_B 1
#define POOM_INPUT_LEFT 2
#define POOM_INPUT_RIGHT 3
#define POOM_INPUT_UP 4
#define POOM_INPUT_DOWN 5
#define POOM_INPUT_COUNT 6

#ifdef __cplusplus
extern "C"
{
#endif

    bool input_init(void);
    void input_deinit(void);
    bool input_read(uint8_t pin);
    uint8_t input_read_all(void);

#ifdef __cplusplus
}
#endif
