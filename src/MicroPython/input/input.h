#pragma once
#include <stdbool.h>

#include "input_buttons.h"

#ifdef __cplusplus
extern "C"
{
#endif

    extern bool input_back_special;
    bool poom_input_mp_init(void);
    void poom_input_mp_deinit(void);
    int poom_input_mp_read(void);
    bool flipper_input_mp_init(void);
    void flipper_input_mp_deinit(void);
    int flipper_input_mp_read(void);
    bool input_noop_init(void);
    void input_noop_deinit(void);
    int input_noop_read(void);
    int input_char_to_button(int c);
    char input_button_to_char(int button, bool shift);

#ifdef __cplusplus
}
#endif