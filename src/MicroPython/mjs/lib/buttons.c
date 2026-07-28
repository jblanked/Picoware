#include "buttons.h"
#include <string.h>
#include "py/runtime.h"

void buttons_create(struct mjs *mjs, mjs_val_t *buttons_obj)
{
    *buttons_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *buttons_obj, "BUTTON_NONE", ~0, mjs_mk_number(mjs, (double)-1));
    mjs_set(mjs, *buttons_obj, "BUTTON_UART", ~0, mjs_mk_number(mjs, (double)-2));
    mjs_set(mjs, *buttons_obj, "BUTTON_PICO_CALC", ~0, mjs_mk_number(mjs, (double)-3));

    mjs_set(mjs, *buttons_obj, "BUTTON_UP", ~0, mjs_mk_number(mjs, (double)0));
    mjs_set(mjs, *buttons_obj, "BUTTON_DOWN", ~0, mjs_mk_number(mjs, (double)1));
    mjs_set(mjs, *buttons_obj, "BUTTON_RIGHT", ~0, mjs_mk_number(mjs, (double)2));
    mjs_set(mjs, *buttons_obj, "BUTTON_LEFT", ~0, mjs_mk_number(mjs, (double)3));
    mjs_set(mjs, *buttons_obj, "BUTTON_CENTER", ~0, mjs_mk_number(mjs, (double)4));
    mjs_set(mjs, *buttons_obj, "BUTTON_OK", ~0, mjs_mk_number(mjs, (double)4));
    mjs_set(mjs, *buttons_obj, "BUTTON_BACK", ~0, mjs_mk_number(mjs, (double)5));
    mjs_set(mjs, *buttons_obj, "BUTTON_START", ~0, mjs_mk_number(mjs, (double)6));

    mjs_set(mjs, *buttons_obj, "BUTTON_A", ~0, mjs_mk_number(mjs, (double)7));
    mjs_set(mjs, *buttons_obj, "BUTTON_B", ~0, mjs_mk_number(mjs, (double)8));
    mjs_set(mjs, *buttons_obj, "BUTTON_C", ~0, mjs_mk_number(mjs, (double)9));
    mjs_set(mjs, *buttons_obj, "BUTTON_D", ~0, mjs_mk_number(mjs, (double)10));
    mjs_set(mjs, *buttons_obj, "BUTTON_E", ~0, mjs_mk_number(mjs, (double)11));
    mjs_set(mjs, *buttons_obj, "BUTTON_F", ~0, mjs_mk_number(mjs, (double)12));
    mjs_set(mjs, *buttons_obj, "BUTTON_G", ~0, mjs_mk_number(mjs, (double)13));
    mjs_set(mjs, *buttons_obj, "BUTTON_H", ~0, mjs_mk_number(mjs, (double)14));
    mjs_set(mjs, *buttons_obj, "BUTTON_I", ~0, mjs_mk_number(mjs, (double)15));
    mjs_set(mjs, *buttons_obj, "BUTTON_J", ~0, mjs_mk_number(mjs, (double)16));
    mjs_set(mjs, *buttons_obj, "BUTTON_K", ~0, mjs_mk_number(mjs, (double)17));
    mjs_set(mjs, *buttons_obj, "BUTTON_L", ~0, mjs_mk_number(mjs, (double)18));
    mjs_set(mjs, *buttons_obj, "BUTTON_M", ~0, mjs_mk_number(mjs, (double)19));
    mjs_set(mjs, *buttons_obj, "BUTTON_N", ~0, mjs_mk_number(mjs, (double)20));
    mjs_set(mjs, *buttons_obj, "BUTTON_O", ~0, mjs_mk_number(mjs, (double)21));
    mjs_set(mjs, *buttons_obj, "BUTTON_P", ~0, mjs_mk_number(mjs, (double)22));
    mjs_set(mjs, *buttons_obj, "BUTTON_Q", ~0, mjs_mk_number(mjs, (double)23));
    mjs_set(mjs, *buttons_obj, "BUTTON_R", ~0, mjs_mk_number(mjs, (double)24));
    mjs_set(mjs, *buttons_obj, "BUTTON_S", ~0, mjs_mk_number(mjs, (double)25));
    mjs_set(mjs, *buttons_obj, "BUTTON_T", ~0, mjs_mk_number(mjs, (double)26));
    mjs_set(mjs, *buttons_obj, "BUTTON_U", ~0, mjs_mk_number(mjs, (double)27));
    mjs_set(mjs, *buttons_obj, "BUTTON_V", ~0, mjs_mk_number(mjs, (double)28));
    mjs_set(mjs, *buttons_obj, "BUTTON_W", ~0, mjs_mk_number(mjs, (double)29));
    mjs_set(mjs, *buttons_obj, "BUTTON_X", ~0, mjs_mk_number(mjs, (double)30));
    mjs_set(mjs, *buttons_obj, "BUTTON_Y", ~0, mjs_mk_number(mjs, (double)31));
    mjs_set(mjs, *buttons_obj, "BUTTON_Z", ~0, mjs_mk_number(mjs, (double)32));

    mjs_set(mjs, *buttons_obj, "BUTTON_0", ~0, mjs_mk_number(mjs, (double)33));
    mjs_set(mjs, *buttons_obj, "BUTTON_1", ~0, mjs_mk_number(mjs, (double)34));
    mjs_set(mjs, *buttons_obj, "BUTTON_2", ~0, mjs_mk_number(mjs, (double)35));
    mjs_set(mjs, *buttons_obj, "BUTTON_3", ~0, mjs_mk_number(mjs, (double)36));
    mjs_set(mjs, *buttons_obj, "BUTTON_4", ~0, mjs_mk_number(mjs, (double)37));
    mjs_set(mjs, *buttons_obj, "BUTTON_5", ~0, mjs_mk_number(mjs, (double)38));
    mjs_set(mjs, *buttons_obj, "BUTTON_6", ~0, mjs_mk_number(mjs, (double)39));
    mjs_set(mjs, *buttons_obj, "BUTTON_7", ~0, mjs_mk_number(mjs, (double)40));
    mjs_set(mjs, *buttons_obj, "BUTTON_8", ~0, mjs_mk_number(mjs, (double)41));
    mjs_set(mjs, *buttons_obj, "BUTTON_9", ~0, mjs_mk_number(mjs, (double)42));

    mjs_set(mjs, *buttons_obj, "BUTTON_SPACE", ~0, mjs_mk_number(mjs, (double)43));
    mjs_set(mjs, *buttons_obj, "BUTTON_EXCLAMATION", ~0, mjs_mk_number(mjs, (double)44));
    mjs_set(mjs, *buttons_obj, "BUTTON_AT", ~0, mjs_mk_number(mjs, (double)45));
    mjs_set(mjs, *buttons_obj, "BUTTON_HASH", ~0, mjs_mk_number(mjs, (double)46));
    mjs_set(mjs, *buttons_obj, "BUTTON_DOLLAR", ~0, mjs_mk_number(mjs, (double)47));
    mjs_set(mjs, *buttons_obj, "BUTTON_PERCENT", ~0, mjs_mk_number(mjs, (double)48));
    mjs_set(mjs, *buttons_obj, "BUTTON_CARET", ~0, mjs_mk_number(mjs, (double)49));
    mjs_set(mjs, *buttons_obj, "BUTTON_AMPERSAND", ~0, mjs_mk_number(mjs, (double)50));
    mjs_set(mjs, *buttons_obj, "BUTTON_ASTERISK", ~0, mjs_mk_number(mjs, (double)51));
    mjs_set(mjs, *buttons_obj, "BUTTON_LEFT_PARENTHESIS", ~0, mjs_mk_number(mjs, (double)52));
    mjs_set(mjs, *buttons_obj, "BUTTON_RIGHT_PARENTHESIS", ~0, mjs_mk_number(mjs, (double)53));
    mjs_set(mjs, *buttons_obj, "BUTTON_MINUS", ~0, mjs_mk_number(mjs, (double)54));
    mjs_set(mjs, *buttons_obj, "BUTTON_UNDERSCORE", ~0, mjs_mk_number(mjs, (double)55));
    mjs_set(mjs, *buttons_obj, "BUTTON_PLUS", ~0, mjs_mk_number(mjs, (double)56));
    mjs_set(mjs, *buttons_obj, "BUTTON_EQUAL", ~0, mjs_mk_number(mjs, (double)57));
    mjs_set(mjs, *buttons_obj, "BUTTON_LEFT_BRACKET", ~0, mjs_mk_number(mjs, (double)58));
    mjs_set(mjs, *buttons_obj, "BUTTON_RIGHT_BRACKET", ~0, mjs_mk_number(mjs, (double)59));
    mjs_set(mjs, *buttons_obj, "BUTTON_LEFT_BRACE", ~0, mjs_mk_number(mjs, (double)60));
    mjs_set(mjs, *buttons_obj, "BUTTON_RIGHT_BRACE", ~0, mjs_mk_number(mjs, (double)61));
    mjs_set(mjs, *buttons_obj, "BUTTON_SEMICOLON", ~0, mjs_mk_number(mjs, (double)62));
    mjs_set(mjs, *buttons_obj, "BUTTON_COLON", ~0, mjs_mk_number(mjs, (double)63));
    mjs_set(mjs, *buttons_obj, "BUTTON_SINGLE_QUOTE", ~0, mjs_mk_number(mjs, (double)64));
    mjs_set(mjs, *buttons_obj, "BUTTON_DOUBLE_QUOTE", ~0, mjs_mk_number(mjs, (double)65));
    mjs_set(mjs, *buttons_obj, "BUTTON_COMMA", ~0, mjs_mk_number(mjs, (double)66));
    mjs_set(mjs, *buttons_obj, "BUTTON_PERIOD", ~0, mjs_mk_number(mjs, (double)67));
    mjs_set(mjs, *buttons_obj, "BUTTON_SLASH", ~0, mjs_mk_number(mjs, (double)68));
    mjs_set(mjs, *buttons_obj, "BUTTON_BACKSLASH", ~0, mjs_mk_number(mjs, (double)69));
    mjs_set(mjs, *buttons_obj, "BUTTON_LESS_THAN", ~0, mjs_mk_number(mjs, (double)70));
    mjs_set(mjs, *buttons_obj, "BUTTON_GREATER_THAN", ~0, mjs_mk_number(mjs, (double)71));
    mjs_set(mjs, *buttons_obj, "BUTTON_QUESTION", ~0, mjs_mk_number(mjs, (double)72));
    mjs_set(mjs, *buttons_obj, "BUTTON_BACKSPACE", ~0, mjs_mk_number(mjs, (double)73));
    mjs_set(mjs, *buttons_obj, "BUTTON_ENTER", ~0, mjs_mk_number(mjs, (double)74));
    mjs_set(mjs, *buttons_obj, "BUTTON_SHIFT", ~0, mjs_mk_number(mjs, (double)75));
    mjs_set(mjs, *buttons_obj, "BUTTON_CAPS_LOCK", ~0, mjs_mk_number(mjs, (double)76));
    mjs_set(mjs, *buttons_obj, "BUTTON_ESCAPE", ~0, mjs_mk_number(mjs, (double)77));
    mjs_set(mjs, *buttons_obj, "BUTTON_CONTROL", ~0, mjs_mk_number(mjs, (double)78));
    mjs_set(mjs, *buttons_obj, "BUTTON_ALT", ~0, mjs_mk_number(mjs, (double)79));
    mjs_set(mjs, *buttons_obj, "BUTTON_HOME", ~0, mjs_mk_number(mjs, (double)80));
    mjs_set(mjs, *buttons_obj, "BUTTON_DELETE", ~0, mjs_mk_number(mjs, (double)81));
    mjs_set(mjs, *buttons_obj, "BUTTON_TAB", ~0, mjs_mk_number(mjs, (double)82));
    mjs_set(mjs, *buttons_obj, "BUTTON_TILDE", ~0, mjs_mk_number(mjs, (double)83));
    mjs_set(mjs, *buttons_obj, "BUTTON_PIPE", ~0, mjs_mk_number(mjs, (double)84));
    mjs_set(mjs, *buttons_obj, "BUTTON_BACK_TICK", ~0, mjs_mk_number(mjs, (double)85));
    mjs_set(mjs, *buttons_obj, "BUTTON_END", ~0, mjs_mk_number(mjs, (double)86));
    mjs_set(mjs, *buttons_obj, "BUTTON_F1", ~0, mjs_mk_number(mjs, (double)87));
    mjs_set(mjs, *buttons_obj, "BUTTON_F2", ~0, mjs_mk_number(mjs, (double)88));
    mjs_set(mjs, *buttons_obj, "BUTTON_F3", ~0, mjs_mk_number(mjs, (double)89));
    mjs_set(mjs, *buttons_obj, "BUTTON_F4", ~0, mjs_mk_number(mjs, (double)90));
    mjs_set(mjs, *buttons_obj, "BUTTON_F5", ~0, mjs_mk_number(mjs, (double)91));
    mjs_set(mjs, *buttons_obj, "BUTTON_F6", ~0, mjs_mk_number(mjs, (double)92));
    mjs_set(mjs, *buttons_obj, "BUTTON_F7", ~0, mjs_mk_number(mjs, (double)93));
    mjs_set(mjs, *buttons_obj, "BUTTON_F8", ~0, mjs_mk_number(mjs, (double)94));
    mjs_set(mjs, *buttons_obj, "BUTTON_F9", ~0, mjs_mk_number(mjs, (double)95));
    mjs_set(mjs, *buttons_obj, "BUTTON_F10", ~0, mjs_mk_number(mjs, (double)96));
    mjs_set(mjs, *buttons_obj, "BUTTON_CTRL_UP", ~0, mjs_mk_number(mjs, (double)97));
    mjs_set(mjs, *buttons_obj, "BUTTON_CTRL_DOWN", ~0, mjs_mk_number(mjs, (double)98));

    mjs_set(mjs, *buttons_obj, "KEY_MOD_ALT", ~0, mjs_mk_number(mjs, (double)0xA1));
    mjs_set(mjs, *buttons_obj, "KEY_MOD_SHL", ~0, mjs_mk_number(mjs, (double)0xA2));
    mjs_set(mjs, *buttons_obj, "KEY_MOD_SHR", ~0, mjs_mk_number(mjs, (double)0xA3));
    mjs_set(mjs, *buttons_obj, "KEY_MOD_SYM", ~0, mjs_mk_number(mjs, (double)0xA4));
    mjs_set(mjs, *buttons_obj, "KEY_MOD_CTRL", ~0, mjs_mk_number(mjs, (double)0xA5));
    mjs_set(mjs, *buttons_obj, "KEY_CTRL_UP", ~0, mjs_mk_number(mjs, (double)0xC2));
    mjs_set(mjs, *buttons_obj, "KEY_CTRL_DOWN", ~0, mjs_mk_number(mjs, (double)0xC3));

    mjs_set(mjs, *buttons_obj, "KEY_ESC", ~0, mjs_mk_number(mjs, (double)0xB1));
    mjs_set(mjs, *buttons_obj, "KEY_UP", ~0, mjs_mk_number(mjs, (double)0xB5));
    mjs_set(mjs, *buttons_obj, "KEY_DOWN", ~0, mjs_mk_number(mjs, (double)0xB6));
    mjs_set(mjs, *buttons_obj, "KEY_LEFT", ~0, mjs_mk_number(mjs, (double)0xB4));
    mjs_set(mjs, *buttons_obj, "KEY_RIGHT", ~0, mjs_mk_number(mjs, (double)0xB7));

    mjs_set(mjs, *buttons_obj, "KEY_BREAK", ~0, mjs_mk_number(mjs, (double)0xD0));
    mjs_set(mjs, *buttons_obj, "KEY_INSERT", ~0, mjs_mk_number(mjs, (double)0xD1));
    mjs_set(mjs, *buttons_obj, "KEY_HOME", ~0, mjs_mk_number(mjs, (double)0xD2));
    mjs_set(mjs, *buttons_obj, "KEY_DEL", ~0, mjs_mk_number(mjs, (double)0xD4));
    mjs_set(mjs, *buttons_obj, "KEY_END", ~0, mjs_mk_number(mjs, (double)0xD5));
    mjs_set(mjs, *buttons_obj, "KEY_PAGE_UP", ~0, mjs_mk_number(mjs, (double)0xD6));
    mjs_set(mjs, *buttons_obj, "KEY_PAGE_DOWN", ~0, mjs_mk_number(mjs, (double)0xD7));

    mjs_set(mjs, *buttons_obj, "KEY_CAPS_LOCK", ~0, mjs_mk_number(mjs, (double)0xC1));

    mjs_set(mjs, *buttons_obj, "KEY_F1", ~0, mjs_mk_number(mjs, (double)0x81));
    mjs_set(mjs, *buttons_obj, "KEY_F2", ~0, mjs_mk_number(mjs, (double)0x82));
    mjs_set(mjs, *buttons_obj, "KEY_F3", ~0, mjs_mk_number(mjs, (double)0x83));
    mjs_set(mjs, *buttons_obj, "KEY_F4", ~0, mjs_mk_number(mjs, (double)0x84));
    mjs_set(mjs, *buttons_obj, "KEY_F5", ~0, mjs_mk_number(mjs, (double)0x85));
    mjs_set(mjs, *buttons_obj, "KEY_F6", ~0, mjs_mk_number(mjs, (double)0x86));
    mjs_set(mjs, *buttons_obj, "KEY_F7", ~0, mjs_mk_number(mjs, (double)0x87));
    mjs_set(mjs, *buttons_obj, "KEY_F8", ~0, mjs_mk_number(mjs, (double)0x88));
    mjs_set(mjs, *buttons_obj, "KEY_F9", ~0, mjs_mk_number(mjs, (double)0x89));
    mjs_set(mjs, *buttons_obj, "KEY_F10", ~0, mjs_mk_number(mjs, (double)0x90));
}