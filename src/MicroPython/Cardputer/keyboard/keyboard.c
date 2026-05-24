#include "keyboard.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "keyboard";

static i2c_master_bus_handle_t s_i2c_bus;
static i2c_master_dev_handle_t s_tca_dev;
static bool s_fn_pressed;
static bool s_caps_lock;

enum
{
    REG_CFG = 0x01,
    REG_INT_STAT = 0x02,
    REG_KEY_LCK_EC = 0x03,
    REG_KEY_EVENT_A = 0x04,
    REG_KP_GPIO1 = 0x1D,
    REG_KP_GPIO2 = 0x1E,
    REG_KP_GPIO3 = 0x1F,
    REG_GPI_EM1 = 0x20,
    REG_GPI_EM2 = 0x21,
    REG_GPI_EM3 = 0x22,
};

static esp_err_t tca_write(uint8_t reg, uint8_t value)
{
    uint8_t payload[2] = {reg, value};
    return i2c_master_transmit(s_tca_dev, payload, sizeof(payload), -1);
}

static esp_err_t tca_read(uint8_t reg, uint8_t *value)
{
    return i2c_master_transmit_receive(s_tca_dev, &reg, 1, value, 1, -1);
}

static bool is_alpha_ascii(char value)
{
    return (value >= 'a' && value <= 'z') || (value >= 'A' && value <= 'Z');
}

static char apply_caps_lock(char value)
{
    if (!s_caps_lock || !is_alpha_ascii(value))
    {
        return value;
    }

    if (value >= 'a' && value <= 'z')
    {
        return (char)(value - ('a' - 'A'));
    }

    return (char)(value + ('a' - 'A'));
}

static char map_keycode_to_ascii(uint8_t keycode, bool pressed)
{
    if (keycode == KEYCODE_FN)
    {
        s_fn_pressed = pressed;
        return 0;
    }

    if (keycode == KEYCODE_CAPS)
    {
        if (pressed)
        {
            s_caps_lock = !s_caps_lock;
        }
        return 0;
    }

    char normal = 0;
    char fn = 0;

    switch (keycode)
    {
    case KEYCODE_ESC:
        normal = (char)KEY_ESC;
        fn = (char)KEY_ESC;
        break;
    case KEYCODE_TAB:
        normal = (char)KEY_TAB;
        fn = (char)KEY_TAB;
        break;
    case KEYCODE_CTRL:
        normal = (char)KEY_CTRL;
        fn = (char)KEY_CTRL;
        break;
    case 5:
        normal = '1';
        fn = '!';
        break;
    case 6:
        normal = 'q';
        fn = 'Q';
        break;
    case KEYCODE_OPT:
        normal = (char)KEY_OPT;
        fn = (char)KEY_OPT;
        break;
    case 11:
        normal = '2';
        fn = '@';
        break;
    case 12:
        normal = 'w';
        fn = 'W';
        break;
    case 13:
        normal = 'a';
        fn = 'A';
        break;
    case KEYCODE_ALT:
        normal = (char)KEY_ALT;
        fn = (char)KEY_ALT;
        break;
    case 15:
        normal = '3';
        fn = '#';
        break;
    case 16:
        normal = 'e';
        fn = 'E';
        break;
    case 17:
        normal = 's';
        fn = 'S';
        break;
    case 18:
        normal = 'z';
        fn = 'Z';
        break;
    case 21:
        normal = '4';
        fn = '$';
        break;
    case 22:
        normal = 'r';
        fn = 'R';
        break;
    case 23:
        normal = 'd';
        fn = 'D';
        break;
    case 24:
        normal = 'x';
        fn = 'X';
        break;
    case 25:
        normal = '5';
        fn = '%';
        break;
    case 26:
        normal = 't';
        fn = 'T';
        break;
    case 27:
        normal = 'f';
        fn = 'F';
        break;
    case 28:
        normal = 'c';
        fn = 'C';
        break;
    case 31:
        normal = '6';
        fn = '^';
        break;
    case 32:
        normal = 'y';
        fn = 'Y';
        break;
    case 33:
        normal = 'g';
        fn = 'G';
        break;
    case 34:
        normal = 'v';
        fn = 'V';
        break;
    case 35:
        normal = '7';
        fn = '&';
        break;
    case 36:
        normal = 'u';
        fn = 'U';
        break;
    case 37:
        normal = 'h';
        fn = 'H';
        break;
    case 38:
        normal = 'b';
        fn = 'B';
        break;
    case 41:
        normal = '8';
        fn = '*';
        break;
    case 42:
        normal = 'i';
        fn = 'I';
        break;
    case 43:
        normal = 'j';
        fn = 'J';
        break;
    case 44:
        normal = 'n';
        fn = 'N';
        break;
    case 45:
        normal = '9';
        fn = '(';
        break;
    case 46:
        normal = 'o';
        fn = 'O';
        break;
    case 47:
        normal = 'k';
        fn = 'K';
        break;
    case 48:
        normal = 'm';
        fn = 'M';
        break;
    case 51:
        normal = '0';
        fn = ')';
        break;
    case 52:
        normal = 'p';
        fn = 'P';
        break;
    case 53:
        normal = 'l';
        fn = 'L';
        break;
    case KEYCODE_LEFT:
        normal = (char)KEY_LEFT;
        fn = ',';
        break;
    case 55:
        normal = '-';
        fn = '_';
        break;
    case 56:
        normal = '[';
        fn = '{';
        break;
    case KEYCODE_UP:
        normal = (char)KEY_UP;
        fn = ';';
        break;
    case KEYCODE_DOWN:
        normal = (char)KEY_DOWN;
        fn = '.';
        break;
    case 61:
        normal = '=';
        fn = '+';
        break;
    case 62:
        normal = ']';
        fn = '}';
        break;
    case 63:
        normal = '\'';
        fn = '"';
        break;
    case KEYCODE_RIGHT:
        normal = (char)KEY_RIGHT;
        fn = '/';
        break;
    case KEYCODE_BACKSPACE:
        normal = (char)KEY_BACKSPACE;
        fn = (char)KEY_BACKSPACE;
        break;
    case 66:
        normal = '\\';
        fn = '|';
        break;
    case KEYCODE_ENTER:
        normal = (char)KEY_ENTER;
        fn = (char)KEY_ENTER;
        break;
    case KEYCODE_SPACE:
        normal = ' ';
        fn = ' ';
        break;
    default:
        return 0;
    }

    return apply_caps_lock(s_fn_pressed ? fn : normal);
}

static esp_err_t keyboard_clear_interrupt(void)
{
    uint8_t int_status = 0;
    ESP_RETURN_ON_ERROR(tca_read(REG_INT_STAT, &int_status), TAG,
                        "failed to read int status");
    ESP_RETURN_ON_ERROR(tca_write(REG_INT_STAT, int_status), TAG,
                        "failed to clear int status");
    return ESP_OK;
}

esp_err_t keyboard_init(void)
{
    if (s_tca_dev != NULL)
    {
        return ESP_OK;
    }

    if (s_i2c_bus == NULL)
    {
        i2c_master_bus_config_t bus_cfg = {
            .i2c_port = CARDPUTER_I2C_PORT,
            .sda_io_num = CARDPUTER_I2C_SDA_GPIO,
            .scl_io_num = CARDPUTER_I2C_SCL_GPIO,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .flags.enable_internal_pullup = true,
        };
        ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus_cfg, &s_i2c_bus), TAG,
                            "i2c bus init failed");
    }

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = CARDPUTER_KEYBOARD_I2C_ADDR,
        .scl_speed_hz = CARDPUTER_I2C_FREQ_HZ,
    };
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(s_i2c_bus, &dev_cfg, &s_tca_dev), TAG,
                        "failed to add keyboard device");

    gpio_config_t int_cfg = {
        .pin_bit_mask = 1ULL << CARDPUTER_KEYBOARD_INT_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&int_cfg), TAG, "keyboard int gpio config failed");

    // TI datasheet row/column matrix setup for 7x8 keypad mode.
    ESP_RETURN_ON_ERROR(tca_write(REG_KP_GPIO1, 0x7F), TAG, "KP_GPIO1 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_KP_GPIO2, 0xFF), TAG, "KP_GPIO2 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_KP_GPIO3, 0x00), TAG, "KP_GPIO3 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_GPI_EM1, 0x00), TAG, "GPI_EM1 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_GPI_EM2, 0x00), TAG, "GPI_EM2 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_GPI_EM3, 0x00), TAG, "GPI_EM3 write failed");
    ESP_RETURN_ON_ERROR(tca_write(REG_CFG, 0x01), TAG, "CFG write failed");

    ESP_RETURN_ON_ERROR(keyboard_clear_interrupt(), TAG, "keyboard int clear failed");
    return ESP_OK;
}

bool keyboard_irq_asserted(void)
{
    return gpio_get_level(CARDPUTER_KEYBOARD_INT_GPIO) == 0;
}

esp_err_t keyboard_read_event(keyboard_event_t *out_event, bool *has_event)
{
    if (out_event == NULL || has_event == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_tca_dev == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t key_event_count = 0;
    ESP_RETURN_ON_ERROR(tca_read(REG_KEY_LCK_EC, &key_event_count), TAG,
                        "failed to read key event count");

    if ((key_event_count & 0x0F) == 0)
    {
        *has_event = false;
        return ESP_OK;
    }

    uint8_t event_byte = 0;
    ESP_RETURN_ON_ERROR(tca_read(REG_KEY_EVENT_A, &event_byte), TAG,
                        "failed to read key event");

    out_event->pressed = (event_byte & 0x80) != 0;
    out_event->keycode = (event_byte & 0x7F);
    out_event->ascii = map_keycode_to_ascii(out_event->keycode, out_event->pressed);
    *has_event = true;

    ESP_RETURN_ON_ERROR(keyboard_clear_interrupt(), TAG, "keyboard int clear failed");
    return ESP_OK;
}
