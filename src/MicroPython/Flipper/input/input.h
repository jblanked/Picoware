#pragma once

#include <stdbool.h>
#include <stdint.h>

#define FLIPPER_INPUT_UP 0
#define FLIPPER_INPUT_DOWN 1
#define FLIPPER_INPUT_RIGHT 2
#define FLIPPER_INPUT_LEFT 3
#define FLIPPER_INPUT_OK 4
#define FLIPPER_INPUT_BACK 5
#define FLIPPER_INPUT_COUNT 6

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
