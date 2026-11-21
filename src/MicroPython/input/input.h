#pragma once
#include <stdbool.h>

#include "input_buttons.h"

#ifdef __cplusplus
extern "C"
{
#endif

    int input_char_to_button(int c);
    char input_button_to_char(int button, bool shift);

#ifdef __cplusplus
}
#endif