#pragma once
#include <stdbool.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
bool desktop_input_init(void);
void desktop_input_deinit(void);
int desktop_input_read(void);
void input_set_touch(uint16_t x, uint16_t y, uint16_t strength, bool pressed);
void desktop_input_point(uint16_t *x, uint16_t *y);
#ifdef __cplusplus
}
#endif
