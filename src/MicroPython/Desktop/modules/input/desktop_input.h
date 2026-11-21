#pragma once
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
bool desktop_input_init(void);
void desktop_input_deinit(void);
int desktop_input_read(void);
#ifdef __cplusplus
}
#endif
