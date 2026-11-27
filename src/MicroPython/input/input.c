#include "input.h"

bool input_back_special = false;
static InputTouchState touch_state = {0};

const InputTouchState *input_touch_state(void)
{
    return &touch_state;
}

void input_set_touch(uint16_t x, uint16_t y, uint8_t gesture, bool pressed)
{
    touch_state.x = pressed ? x : 0;
    touch_state.y = pressed ? y : 0;
    touch_state.gesture = gesture;
    touch_state.pressed = pressed;
}

bool input_noop_init(void)
{
    return true;
}

void input_noop_deinit(void)
{
}

int input_noop_read(void)
{
    return -1;
}

int input_char_to_button(int c)
{
    switch (c)
    {
    case BUTTON_UP:
        return BUTTON_UP;
    case BUTTON_DOWN:
        return BUTTON_DOWN;
    case BUTTON_LEFT:
        return BUTTON_LEFT;
    case BUTTON_RIGHT:
        return BUTTON_RIGHT;
    case BUTTON_CENTER:
        return BUTTON_CENTER;
    case BUTTON_BACK:
        return input_back_special ? BUTTON_BACKSPACE : BUTTON_BACK;
    case BUTTON_START:
        return BUTTON_START;
    case PICOWARE_KEYCODE_BACKSPACE:
        return BUTTON_BACK;
    case PICOWARE_KEYCODE_TAB:
        return BUTTON_TAB;
    case PICOWARE_KEYCODE_ENTER:
    case PICOWARE_KEYCODE_RETURN:
        return BUTTON_CENTER;
    case PICOWARE_KEYCODE_ESC:
        return input_back_special ? BUTTON_BACK : BUTTON_ESCAPE;
    case PICOWARE_KEYCODE_UP:
        return BUTTON_UP;
    case PICOWARE_KEYCODE_DOWN:
        return BUTTON_DOWN;
    case PICOWARE_KEYCODE_LEFT:
        return BUTTON_LEFT;
    case PICOWARE_KEYCODE_RIGHT:
        return BUTTON_RIGHT;
    case PICOWARE_KEYCODE_HOME:
        return BUTTON_HOME;
    case PICOWARE_KEYCODE_DEL:
        return BUTTON_BACKSPACE;
    case PICOWARE_KEYCODE_END:
        return BUTTON_END;
    case PICOWARE_KEYCODE_CTRL_UP:
        return BUTTON_CTRL_UP;
    case PICOWARE_KEYCODE_CTRL_DOWN:
        return BUTTON_CTRL_DOWN;
    case 32:
        return BUTTON_SPACE;
    case 33:
        return BUTTON_EXCLAMATION;
    case 34:
        return BUTTON_DOUBLE_QUOTE;
    case 35:
        return BUTTON_HASH;
    case 36:
        return BUTTON_DOLLAR;
    case 37:
        return BUTTON_PERCENT;
    case 38:
        return BUTTON_AMPERSAND;
    case 39:
        return BUTTON_SINGLE_QUOTE;
    case 40:
        return BUTTON_LEFT_PARENTHESIS;
    case 41:
        return BUTTON_RIGHT_PARENTHESIS;
    case 42:
        return BUTTON_ASTERISK;
    case 43:
        return BUTTON_PLUS;
    case 44:
        return BUTTON_COMMA;
    case 45:
        return BUTTON_MINUS;
    case 46:
        return BUTTON_PERIOD;
    case 47:
        return BUTTON_SLASH;
    // numbers
    case 48:
        return BUTTON_0;
    case 49:
        return BUTTON_1;
    case 50:
        return BUTTON_2;
    case 51:
        return BUTTON_3;
    case 52:
        return BUTTON_4;
    case 53:
        return BUTTON_5;
    case 54:
        return BUTTON_6;
    case 55:
        return BUTTON_7;
    case 56:
        return BUTTON_8;
    case 57:
        return BUTTON_9;
    // punctuation
    case 58:
        return BUTTON_COLON;
    case 59:
        return BUTTON_SEMICOLON;
    case 60:
        return BUTTON_LESS_THAN;
    case 61:
        return BUTTON_EQUAL;
    case 62:
        return BUTTON_GREATER_THAN;
    case 63:
        return BUTTON_QUESTION;
    case 64:
        return BUTTON_AT;
    // uppercase letters
    case 65:
        return BUTTON_A;
    case 66:
        return BUTTON_B;
    case 67:
        return BUTTON_C;
    case 68:
        return BUTTON_D;
    case 69:
        return BUTTON_E;
    case 70:
        return BUTTON_F;
    case 71:
        return BUTTON_G;
    case 72:
        return BUTTON_H;
    case 73:
        return BUTTON_I;
    case 74:
        return BUTTON_J;
    case 75:
        return BUTTON_K;
    case 76:
        return BUTTON_L;
    case 77:
        return BUTTON_M;
    case 78:
        return BUTTON_N;
    case 79:
        return BUTTON_O;
    case 80:
        return BUTTON_P;
    case 81:
        return BUTTON_Q;
    case 82:
        return BUTTON_R;
    case 83:
        return BUTTON_S;
    case 84:
        return BUTTON_T;
    case 85:
        return BUTTON_U;
    case 86:
        return BUTTON_V;
    case 87:
        return BUTTON_W;
    case 88:
        return BUTTON_X;
    case 89:
        return BUTTON_Y;
    case 90:
        return BUTTON_Z;
    // additional punctuation
    case 91:
        return BUTTON_LEFT_BRACKET;
    case 92:
        return BUTTON_BACKSLASH;
    case 93:
        return BUTTON_RIGHT_BRACKET;
    case 94:
        return BUTTON_CARET;
    case 95:
        return BUTTON_UNDERSCORE;
    case 96:
        return BUTTON_BACK_TICK;
    // lowercase letters
    case 97:
        return BUTTON_A;
    case 98:
        return BUTTON_B;
    case 99:
        return BUTTON_C;
    case 100:
        return BUTTON_D;
    case 101:
        return BUTTON_E;
    case 102:
        return BUTTON_F;
    case 103:
        return BUTTON_G;
    case 104:
        return BUTTON_H;
    case 105:
        return BUTTON_I;
    case 106:
        return BUTTON_J;
    case 107:
        return BUTTON_K;
    case 108:
        return BUTTON_L;
    case 109:
        return BUTTON_M;
    case 110:
        return BUTTON_N;
    case 111:
        return BUTTON_O;
    case 112:
        return BUTTON_P;
    case 113:
        return BUTTON_Q;
    case 114:
        return BUTTON_R;
    case 115:
        return BUTTON_S;
    case 116:
        return BUTTON_T;
    case 117:
        return BUTTON_U;
    case 118:
        return BUTTON_V;
    case 119:
        return BUTTON_W;
    case 120:
        return BUTTON_X;
    case 121:
        return BUTTON_Y;
    case 122:
        return BUTTON_Z;
    case 123:
        return BUTTON_LEFT_BRACE;
    case 124:
        return BUTTON_PIPE;
    case 125:
        return BUTTON_RIGHT_BRACE;
    case 126:
        return BUTTON_TILDE;
    // function keys
    case PICOWARE_KEYCODE_F1:
        return BUTTON_F1;
    case PICOWARE_KEYCODE_F2:
        return BUTTON_F2;
    case PICOWARE_KEYCODE_F3:
        return BUTTON_F3;
    case PICOWARE_KEYCODE_F4:
        return BUTTON_F4;
    case PICOWARE_KEYCODE_F5:
        return BUTTON_F5;
    case PICOWARE_KEYCODE_F6:
        return BUTTON_F6;
    case PICOWARE_KEYCODE_F7:
        return BUTTON_F7;
    case PICOWARE_KEYCODE_F8:
        return BUTTON_F8;
    case PICOWARE_KEYCODE_F9:
        return BUTTON_F9;
    case PICOWARE_KEYCODE_F10:
        return BUTTON_F10;
    case PICOWARE_KEYCODE_CTRL_0:
        return BUTTON_CTRL_0;
    case PICOWARE_KEYCODE_CTRL_1:
        return BUTTON_CTRL_1;
    case PICOWARE_KEYCODE_CTRL_2:
        return BUTTON_CTRL_2;
    case PICOWARE_KEYCODE_CTRL_3:
        return BUTTON_CTRL_3;
    case PICOWARE_KEYCODE_CTRL_4:
        return BUTTON_CTRL_4;
    case PICOWARE_KEYCODE_CTRL_5:
        return BUTTON_CTRL_5;
    case PICOWARE_KEYCODE_CTRL_6:
        return BUTTON_CTRL_6;
    case PICOWARE_KEYCODE_CTRL_7:
        return BUTTON_CTRL_7;
    case PICOWARE_KEYCODE_CTRL_8:
        return BUTTON_CTRL_8;
    case PICOWARE_KEYCODE_CTRL_9:
        return BUTTON_CTRL_9;
    default:
        return BUTTON_NONE;
    }
}

char input_button_to_char(int button, bool shift)
{
    switch (button)
    {
    case BUTTON_A:
        return shift ? 'A' : 'a';
    case BUTTON_B:
        return shift ? 'B' : 'b';
    case BUTTON_C:
        return shift ? 'C' : 'c';
    case BUTTON_D:
        return shift ? 'D' : 'd';
    case BUTTON_E:
        return shift ? 'E' : 'e';
    case BUTTON_F:
        return shift ? 'F' : 'f';
    case BUTTON_G:
        return shift ? 'G' : 'g';
    case BUTTON_H:
        return shift ? 'H' : 'h';
    case BUTTON_I:
        return shift ? 'I' : 'i';
    case BUTTON_J:
        return shift ? 'J' : 'j';
    case BUTTON_K:
        return shift ? 'K' : 'k';
    case BUTTON_L:
        return shift ? 'L' : 'l';
    case BUTTON_M:
        return shift ? 'M' : 'm';
    case BUTTON_N:
        return shift ? 'N' : 'n';
    case BUTTON_O:
        return shift ? 'O' : 'o';
    case BUTTON_P:
        return shift ? 'P' : 'p';
    case BUTTON_Q:
        return shift ? 'Q' : 'q';
    case BUTTON_R:
        return shift ? 'R' : 'r';
    case BUTTON_S:
        return shift ? 'S' : 's';
    case BUTTON_T:
        return shift ? 'T' : 't';
    case BUTTON_U:
        return shift ? 'U' : 'u';
    case BUTTON_V:
        return shift ? 'V' : 'v';
    case BUTTON_W:
        return shift ? 'W' : 'w';
    case BUTTON_X:
        return shift ? 'X' : 'x';
    case BUTTON_Y:
        return shift ? 'Y' : 'y';
    case BUTTON_Z:
        return shift ? 'Z' : 'z';
    case BUTTON_0:
        return '0';
    case BUTTON_1:
        return '1';
    case BUTTON_2:
        return '2';
    case BUTTON_3:
        return '3';
    case BUTTON_4:
        return '4';
    case BUTTON_5:
        return '5';
    case BUTTON_6:
        return '6';
    case BUTTON_7:
        return '7';
    case BUTTON_8:
        return '8';
    case BUTTON_9:
        return '9';
    case BUTTON_CENTER:
        return '\n';
    case BUTTON_SPACE:
        return ' ';
    case BUTTON_PERIOD:
        return '.';
    case BUTTON_QUESTION:
        return '?';
    case BUTTON_COMMA:
        return ',';
    case BUTTON_SEMICOLON:
        return ';';
    case BUTTON_MINUS:
        return '-';
    case BUTTON_EQUAL:
        return '=';
    case BUTTON_LEFT_BRACKET:
        return '[';
    case BUTTON_LEFT_BRACE:
        return '{';
    case BUTTON_RIGHT_BRACKET:
        return ']';
    case BUTTON_RIGHT_BRACE:
        return '}';
    case BUTTON_SLASH:
        return '/';
    case BUTTON_BACKSLASH:
        return '\\';
    case BUTTON_UNDERSCORE:
        return '_';
    case BUTTON_COLON:
        return ':';
    case BUTTON_SINGLE_QUOTE:
        return '\'';
    case BUTTON_DOUBLE_QUOTE:
        return '"';
    case BUTTON_PLUS:
        return '+';
    case BUTTON_EXCLAMATION:
        return '!';
    case BUTTON_AT:
        return '@';
    case BUTTON_HASH:
        return '#';
    case BUTTON_DOLLAR:
        return '$';
    case BUTTON_PERCENT:
        return '%';
    case BUTTON_CARET:
        return '^';
    case BUTTON_AMPERSAND:
        return '&';
    case BUTTON_ASTERISK:
        return '*';
    case BUTTON_LEFT_PARENTHESIS:
        return '(';
    case BUTTON_RIGHT_PARENTHESIS:
        return ')';
    case BUTTON_LESS_THAN:
        return '<';
    case BUTTON_GREATER_THAN:
        return '>';
    case BUTTON_BACK_TICK:
        return '`';
    case BUTTON_TILDE:
        return '~';
    case BUTTON_PIPE:
        return '|';
    // no character for function keys
    case BUTTON_F1:
    case BUTTON_F2:
    case BUTTON_F3:
    case BUTTON_F4:
    case BUTTON_F5:
    case BUTTON_F6:
    case BUTTON_F7:
    case BUTTON_F8:
    case BUTTON_F9:
    case BUTTON_F10:
        return 0;
    default:
        return 0;
    }
}