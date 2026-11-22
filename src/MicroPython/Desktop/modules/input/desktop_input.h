#pragma once
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
bool desktop_input_init(void);
void desktop_input_deinit(void);
int desktop_input_read(void);
void desktop_input_game_mode(bool enable);
#ifdef __cplusplus
}
#endif
