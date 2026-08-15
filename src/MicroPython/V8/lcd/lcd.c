#include "lcd.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/spi_master.h"
#include "esp_check.h"
#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

static const char *TAG = "display";

static esp_lcd_panel_io_handle_t s_panel_io;
static esp_lcd_panel_handle_t s_panel;
static bool s_spi_bus_owned;
static bool s_backlight_ready;
static const FontTable *s_current_font = &Font16;
static uint8_t *s_framebuffer;
static uint16_t s_palette[256];

// machine.SDCard brings this bus up with max_transfer_sz = 4000, so a chunk
// (LCD_WIDTH * LCD_SWAP_LINES * 2) must stay under it. 240 * 8 * 2 = 3840.
#define LCD_SWAP_LINES 8U
#define LCD_BACKLIGHT_TIMER LEDC_TIMER_0
#define LCD_BACKLIGHT_CHANNEL LEDC_CHANNEL_0
#define LCD_BACKLIGHT_DUTY_RES LEDC_TIMER_10_BIT
#define LCD_BACKLIGHT_DUTY_MAX ((1U << 10) - 1U)

static const uint8_t LCD_TEXT_SPACING = 1;
static const uint8_t LCD_LINE_SPACING = 2;
static uint16_t s_swap_buffer[LCD_WIDTH * LCD_SWAP_LINES];

static esp_err_t display_init(void);
static esp_err_t lcd_swap_internal(void);
static void lcd_init_palette(void);
static esp_err_t lcd_wait_for_color_tx_done(void);

static uint8_t lcd_color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static void lcd_init_palette(void)
{
    for (int i = 0; i < 256; i++)
    {
        uint8_t r3 = (i >> 5) & 0x07;
        uint8_t g3 = (i >> 2) & 0x07;
        uint8_t b2 = i & 0x03;

        uint8_t r8 = (r3 * 255) / 7;
        uint8_t g8 = (g3 * 255) / 7;
        uint8_t b8 = (b2 * 255) / 3;

        uint16_t pixel = lcd_color332_to_565(r8, g8, b8);
        s_palette[i] = (uint16_t)((pixel << 8) | (pixel >> 8));
    }
}

static esp_err_t lcd_wait_for_color_tx_done(void)
{
    return esp_lcd_panel_io_tx_param(s_panel_io, -1, NULL, 0);
}

static const FontTable *lcd_font_from_size(FontSize size)
{
    switch (size)
    {
    case FONT_SIZE_XTRA_SMALL:
        return &Font8;
    case FONT_SIZE_SMALL:
        return &Font12;
    case FONT_SIZE_LARGE:
        return &Font20;
    case FONT_SIZE_XTRA_LARGE:
        return &Font24;
    case FONT_SIZE_MEDIUM:
    default:
        return &Font16;
    }
}

static const FontTable *lcd_get_font(void)
{
    return s_current_font != NULL ? s_current_font : &Font16;
}

static uint16_t lcd_text_advance(void)
{
    return (uint16_t)(lcd_get_font()->width + LCD_TEXT_SPACING);
}

static uint16_t lcd_line_advance(void)
{
    return (uint16_t)(lcd_get_font()->height + LCD_LINE_SPACING);
}

static size_t lcd_framebuffer_index(uint16_t x, uint16_t y)
{
    return (size_t)y * LCD_WIDTH + x;
}

static void lcd_draw_hline_clipped(int32_t x, int32_t y, int32_t length, uint8_t color)
{
    if (y < 0 || y >= LCD_HEIGHT || length <= 0)
    {
        return;
    }

    if (x < 0)
    {
        length += x;
        x = 0;
    }

    if (x >= LCD_WIDTH || length <= 0)
    {
        return;
    }

    if (x + length > LCD_WIDTH)
    {
        length = LCD_WIDTH - x;
    }

    uint8_t *row = &s_framebuffer[lcd_framebuffer_index((uint16_t)x, (uint16_t)y)];
    for (int32_t pixel = 0; pixel < length; ++pixel)
    {
        row[pixel] = color;
    }
}

static int32_t lcd_edge_function(int32_t ax, int32_t ay, int32_t bx, int32_t by, int32_t px,
                                 int32_t py)
{
    return (px - ax) * (by - ay) - (py - ay) * (bx - ax);
}

// The IDF has no ILI9341 driver. The ILI9341 shares the ST7789's generic command
// set for everything esp_lcd drives (SWRESET/SLPOUT/COLMOD/MADCTL/CASET/RASET/
// RAMWR), so that driver is reused and only these ILI9341 power/gamma registers
// are written afterwards. Values match the standard ILI9341 init used by
// Adafruit/TFT_eSPI, which this panel is already known to work with.
static esp_err_t lcd_send_ili9341_init(void)
{
    static const uint8_t power_ctrl_b[] = {0x00, 0xC1, 0x30};
    static const uint8_t power_seq[] = {0x64, 0x03, 0x12, 0x81};
    static const uint8_t driver_timing_a[] = {0x85, 0x00, 0x78};
    static const uint8_t power_ctrl_a[] = {0x39, 0x2C, 0x00, 0x34, 0x02};
    static const uint8_t pump_ratio[] = {0x20};
    static const uint8_t driver_timing_b[] = {0x00, 0x00};
    static const uint8_t power_1[] = {0x23};
    static const uint8_t power_2[] = {0x10};
    static const uint8_t vcom_1[] = {0x3E, 0x28};
    static const uint8_t vcom_2[] = {0x86};
    static const uint8_t frame_rate[] = {0x00, 0x18};
    static const uint8_t display_func[] = {0x08, 0x82, 0x27};
    static const uint8_t gamma_3g[] = {0x00};
    static const uint8_t gamma_set[] = {0x01};
    static const uint8_t gamma_positive[] = {0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1,
                                             0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00};
    static const uint8_t gamma_negative[] = {0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1,
                                             0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F};

    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xCF, power_ctrl_b, sizeof(power_ctrl_b)),
                        TAG, "ili9341 power control b failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xED, power_seq, sizeof(power_seq)),
                        TAG, "ili9341 power on seq failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xE8, driver_timing_a, sizeof(driver_timing_a)),
                        TAG, "ili9341 driver timing a failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xCB, power_ctrl_a, sizeof(power_ctrl_a)),
                        TAG, "ili9341 power control a failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xF7, pump_ratio, sizeof(pump_ratio)),
                        TAG, "ili9341 pump ratio failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xEA, driver_timing_b, sizeof(driver_timing_b)),
                        TAG, "ili9341 driver timing b failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xC0, power_1, sizeof(power_1)),
                        TAG, "ili9341 power control 1 failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xC1, power_2, sizeof(power_2)),
                        TAG, "ili9341 power control 2 failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xC5, vcom_1, sizeof(vcom_1)),
                        TAG, "ili9341 vcom 1 failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xC7, vcom_2, sizeof(vcom_2)),
                        TAG, "ili9341 vcom 2 failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xB1, frame_rate, sizeof(frame_rate)),
                        TAG, "ili9341 frame rate failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xB6, display_func, sizeof(display_func)),
                        TAG, "ili9341 display function failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xF2, gamma_3g, sizeof(gamma_3g)),
                        TAG, "ili9341 gamma 3g failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0x26, gamma_set, sizeof(gamma_set)),
                        TAG, "ili9341 gamma set failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xE0, gamma_positive, sizeof(gamma_positive)),
                        TAG, "ili9341 positive gamma failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(s_panel_io, 0xE1, gamma_negative, sizeof(gamma_negative)),
                        TAG, "ili9341 negative gamma failed");

    vTaskDelay(pdMS_TO_TICKS(120));
    return ESP_OK;
}

static esp_err_t lcd_setup_backlight(void)
{
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LCD_BACKLIGHT_DUTY_RES,
        .timer_num = LCD_BACKLIGHT_TIMER,
        .freq_hz = LCD_BACKLIGHT_PWM_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_RETURN_ON_ERROR(ledc_timer_config(&timer_cfg), TAG, "backlight timer config failed");

    ledc_channel_config_t channel_cfg = {
        .gpio_num = V8_LCD_BL_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LCD_BACKLIGHT_CHANNEL,
        .timer_sel = LCD_BACKLIGHT_TIMER,
        .intr_type = LEDC_INTR_DISABLE,
        .duty = 0,
        .hpoint = 0,
    };
    ESP_RETURN_ON_ERROR(ledc_channel_config(&channel_cfg), TAG, "backlight channel config failed");

    s_backlight_ready = true;
    return ESP_OK;
}

static esp_err_t display_setup_panel(void)
{
    ESP_RETURN_ON_ERROR(lcd_setup_backlight(), TAG, "backlight setup failed");

    // Claim MISO too: whichever driver initializes the bus fixes its pin map.
    spi_bus_config_t bus_cfg = {
        .sclk_io_num = V8_LCD_SCLK_GPIO,
        .mosi_io_num = V8_LCD_MOSI_GPIO,
        .miso_io_num = V8_LCD_MISO_GPIO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = LCD_WIDTH * LCD_SWAP_LINES * sizeof(uint16_t),
    };

    esp_err_t err = spi_bus_initialize(V8_LCD_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE)
    {
        return err;
    }
    // ESP_ERR_INVALID_STATE means the SD card already owns the bus.
    s_spi_bus_owned = (err == ESP_OK);

    esp_lcd_panel_io_spi_config_t io_cfg = {
        .dc_gpio_num = V8_LCD_DC_GPIO,
        .cs_gpio_num = V8_LCD_CS_GPIO,
        .pclk_hz = 20 * 1000 * 1000,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
        .spi_mode = 0,
        .trans_queue_depth = 1,
    };
    ESP_RETURN_ON_ERROR(
        esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)V8_LCD_HOST, &io_cfg, &s_panel_io),
        TAG, "failed to create panel io");

    // reset_gpio_num = -1 (GPIO_NUM_NC): reset is tied to EN in hardware, so the
    // driver falls back to a software reset (SWRESET), which is fine here.
    esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = V8_LCD_RST_GPIO,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_BGR,
        .bits_per_pixel = 16,
    };
    ESP_RETURN_ON_ERROR(esp_lcd_new_panel_st7789(s_panel_io, &panel_cfg, &s_panel), TAG,
                        "failed to create ili9341 panel");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_reset(s_panel), TAG, "panel reset failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_init(s_panel), TAG, "panel init failed");
    ESP_RETURN_ON_ERROR(lcd_send_ili9341_init(), TAG, "ili9341 init failed");

    // Native portrait, so no swap_xy. MADCTL 0x48 = MX | BGR, as TFT_eSPI uses
    // for the ILI9341 at rotation 0 (the BGR half comes from rgb_ele_order).
    ESP_RETURN_ON_ERROR(esp_lcd_panel_mirror(s_panel, true, false), TAG,
                        "failed to set mirror");
    // ILI9341 defaults to non-inverted colour (unlike the ST7796).
    ESP_RETURN_ON_ERROR(esp_lcd_panel_invert_color(s_panel, false), TAG,
                        "failed to set invert color");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_disp_on_off(s_panel, true), TAG, "failed to enable panel");

    return ESP_OK;
}

static esp_err_t lcd_swap_internal(void)
{
    if (s_panel == NULL || s_framebuffer == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    for (uint16_t y = 0; y < LCD_HEIGHT; y += LCD_SWAP_LINES)
    {
        uint16_t chunk_height = LCD_SWAP_LINES;
        if (y + chunk_height > LCD_HEIGHT)
        {
            chunk_height = LCD_HEIGHT - y;
        }

        for (uint16_t row = 0; row < chunk_height; ++row)
        {
            size_t src_offset = lcd_framebuffer_index(0, (uint16_t)(y + row));
            size_t dst_offset = (size_t)row * LCD_WIDTH;
            for (uint16_t x = 0; x < LCD_WIDTH; ++x)
            {
                s_swap_buffer[dst_offset + x] = s_palette[s_framebuffer[src_offset + x]];
            }
        }

        esp_err_t err =
            esp_lcd_panel_draw_bitmap(s_panel, 0, y, LCD_WIDTH, y + chunk_height, s_swap_buffer);
        if (err != ESP_OK)
        {
            return err;
        }

        err = lcd_wait_for_color_tx_done();
        if (err != ESP_OK)
        {
            return err;
        }
    }

    return ESP_OK;
}

static esp_err_t lcd_alloc_framebuffer(void)
{
    if (s_framebuffer != NULL)
    {
        return ESP_OK;
    }

    // 150 KB at 320x480; only fits in PSRAM.
    s_framebuffer = heap_caps_malloc((size_t)LCD_WIDTH * LCD_HEIGHT, MALLOC_CAP_SPIRAM);
    if (s_framebuffer == NULL)
    {
        ESP_LOGE(TAG, "failed to allocate %d byte framebuffer in PSRAM",
                 LCD_WIDTH * LCD_HEIGHT);
        return ESP_ERR_NO_MEM;
    }

    return ESP_OK;
}

static esp_err_t display_init(void)
{
    if (s_panel != NULL)
    {
        return ESP_OK;
    }

    esp_err_t err = lcd_alloc_framebuffer();
    if (err != ESP_OK)
    {
        return err;
    }

    err = display_setup_panel();
    if (err != ESP_OK)
    {
        lcd_deinit();
        return err;
    }

    lcd_set_font(FONT_DEFAULT);
    lcd_init_palette();
    lcd_fill(0x0000);

    err = lcd_swap_internal();
    if (err != ESP_OK)
    {
        lcd_deinit();
        return err;
    }

    // Backlight on only once a black frame is up, so boot doesn't flash noise.
    if (!lcd_set_backlight(LCD_DEFAULT_BRIGHTNESS))
    {
        lcd_deinit();
        return ESP_FAIL;
    }

    return ESP_OK;
}

bool lcd_init(void)
{
    return display_init() == ESP_OK;
}

void lcd_deinit(void)
{
    if (s_backlight_ready)
    {
        lcd_set_backlight(0);
        ledc_stop(LEDC_LOW_SPEED_MODE, LCD_BACKLIGHT_CHANNEL, 0);
        s_backlight_ready = false;
    }

    if (s_panel != NULL)
    {
        esp_lcd_panel_disp_on_off(s_panel, false);
        esp_lcd_panel_del(s_panel);
        s_panel = NULL;
    }

    if (s_panel_io != NULL)
    {
        esp_lcd_panel_io_del(s_panel_io);
        s_panel_io = NULL;
    }

    if (s_spi_bus_owned)
    {
        spi_bus_free(V8_LCD_HOST);
        s_spi_bus_owned = false;
    }

    if (s_framebuffer != NULL)
    {
        heap_caps_free(s_framebuffer);
        s_framebuffer = NULL;
    }
}

bool lcd_set_backlight(uint32_t brightness)
{
    if (!s_backlight_ready)
    {
        return false;
    }

    if (brightness > 100)
    {
        brightness = 100;
    }

    uint32_t duty = (brightness * LCD_BACKLIGHT_DUTY_MAX) / 100U;
    if (ledc_set_duty(LEDC_LOW_SPEED_MODE, LCD_BACKLIGHT_CHANNEL, duty) != ESP_OK)
    {
        return false;
    }

    return ledc_update_duty(LEDC_LOW_SPEED_MODE, LCD_BACKLIGHT_CHANNEL) == ESP_OK;
}

void lcd_swap(void)
{
    esp_err_t err = lcd_swap_internal();
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "lcd_swap failed: %s", esp_err_to_name(err));
    }
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT || s_framebuffer == NULL)
    {
        return;
    }

    s_framebuffer[lcd_framebuffer_index(x, y)] = lcd_color565_to_332(color);
}

void lcd_fill(uint16_t color)
{
    if (s_framebuffer == NULL)
    {
        return;
    }

    memset(s_framebuffer, lcd_color565_to_332(color), (size_t)LCD_WIDTH * LCD_HEIGHT);
}

void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    if (buffer == NULL || s_framebuffer == NULL || x >= LCD_WIDTH || y >= LCD_HEIGHT ||
        width == 0 || height == 0)
    {
        return;
    }

    uint16_t copy_width = width;
    uint16_t copy_height = height;
    if (x + copy_width > LCD_WIDTH)
    {
        copy_width = LCD_WIDTH - x;
    }
    if (y + copy_height > LCD_HEIGHT)
    {
        copy_height = LCD_HEIGHT - y;
    }

    for (uint16_t row = 0; row < copy_height; ++row)
    {
        memcpy(&s_framebuffer[lcd_framebuffer_index(x, y + row)], &buffer[(size_t)row * width],
               copy_width * sizeof(uint8_t));
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                    const uint16_t *buffer)
{
    if (buffer == NULL || s_framebuffer == NULL || x >= LCD_WIDTH || y >= LCD_HEIGHT ||
        width == 0 || height == 0)
    {
        return;
    }

    uint16_t copy_width = width;
    uint16_t copy_height = height;
    if (x + copy_width > LCD_WIDTH)
    {
        copy_width = LCD_WIDTH - x;
    }
    if (y + copy_height > LCD_HEIGHT)
    {
        copy_height = LCD_HEIGHT - y;
    }

    for (uint16_t row = 0; row < copy_height; ++row)
    {
        const uint16_t *src_row = &buffer[(size_t)row * width];
        uint8_t *dst_row = &s_framebuffer[lcd_framebuffer_index(x, y + row)];

        for (uint16_t col = 0; col < copy_width; ++col)
        {
            dst_row[col] = lcd_color565_to_332(src_row[col]);
        }
    }
}

void lcd_read_row(uint16_t y, uint8_t *out_buffer)
{
    if (out_buffer == NULL || s_framebuffer == NULL || y >= LCD_HEIGHT)
    {
        return;
    }

    memcpy(out_buffer, &s_framebuffer[lcd_framebuffer_index(0, y)], LCD_WIDTH);
}

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    int32_t current_x = x1;
    int32_t current_y = y1;
    const int32_t target_x = x2;
    const int32_t target_y = y2;
    const int32_t delta_x = abs(target_x - current_x);
    const int32_t step_x = current_x < target_x ? 1 : -1;
    const int32_t delta_y = -abs(target_y - current_y);
    const int32_t step_y = current_y < target_y ? 1 : -1;
    int32_t error = delta_x + delta_y;

    while (true)
    {
        if (current_x >= 0 && current_x < LCD_WIDTH && current_y >= 0 && current_y < LCD_HEIGHT)
        {
            lcd_draw_pixel((uint16_t)current_x, (uint16_t)current_y, color);
        }

        if (current_x == target_x && current_y == target_y)
        {
            break;
        }

        int32_t twice_error = error * 2;
        if (twice_error >= delta_y)
        {
            error += delta_y;
            current_x += step_x;
        }
        if (twice_error <= delta_x)
        {
            error += delta_x;
            current_y += step_y;
        }
    }
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    if (width == 0 || height == 0)
    {
        return;
    }

    uint8_t c = lcd_color565_to_332(color);
    lcd_draw_hline_clipped(x, y, width, c);
    lcd_draw_hline_clipped(x, (int32_t)y + height - 1, width, c);
    lcd_draw_line(x, y, x, y + height - 1, color);
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);
}

void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT || width == 0 || height == 0)
    {
        return;
    }

    uint16_t fill_width = width;
    uint16_t fill_height = height;
    if (x + fill_width > LCD_WIDTH)
    {
        fill_width = LCD_WIDTH - x;
    }
    if (y + fill_height > LCD_HEIGHT)
    {
        fill_height = LCD_HEIGHT - y;
    }

    uint8_t c = lcd_color565_to_332(color);
    for (uint16_t row = 0; row < fill_height; ++row)
    {
        lcd_draw_hline_clipped(x, y + row, fill_width, c);
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int32_t x = radius;
    int32_t y = 0;
    int32_t decision = 1 - x;

    while (x >= y)
    {
        lcd_draw_pixel(center_x + x, center_y + y, color);
        lcd_draw_pixel(center_x + y, center_y + x, color);
        lcd_draw_pixel(center_x - y, center_y + x, color);
        lcd_draw_pixel(center_x - x, center_y + y, color);
        lcd_draw_pixel(center_x - x, center_y - y, color);
        lcd_draw_pixel(center_x - y, center_y - x, color);
        lcd_draw_pixel(center_x + y, center_y - x, color);
        lcd_draw_pixel(center_x + x, center_y - y, color);

        ++y;
        if (decision <= 0)
        {
            decision += 2 * y + 1;
        }
        else
        {
            --x;
            decision += 2 * (y - x) + 1;
        }
    }
}

void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int32_t x = radius;
    int32_t y = 0;
    int32_t decision = 1 - x;

    uint8_t c = lcd_color565_to_332(color);
    while (x >= y)
    {
        lcd_draw_hline_clipped((int32_t)center_x - x, center_y + y, 2 * x + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - x, center_y - y, 2 * x + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - y, center_y + x, 2 * y + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - y, center_y - x, 2 * y + 1, c);

        ++y;
        if (decision <= 0)
        {
            decision += 2 * y + 1;
        }
        else
        {
            --x;
            decision += 2 * (y - x) + 1;
        }
    }
}

void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3,
                       uint16_t y3, uint16_t color)
{
    if (s_framebuffer == NULL)
    {
        return;
    }

    int32_t min_x = x1;
    int32_t max_x = x1;
    int32_t min_y = y1;
    int32_t max_y = y1;

    if (x2 < min_x)
        min_x = x2;
    if (x3 < min_x)
        min_x = x3;
    if (x2 > max_x)
        max_x = x2;
    if (x3 > max_x)
        max_x = x3;
    if (y2 < min_y)
        min_y = y2;
    if (y3 < min_y)
        min_y = y3;
    if (y2 > max_y)
        max_y = y2;
    if (y3 > max_y)
        max_y = y3;

    if (max_x < 0 || max_y < 0 || min_x >= LCD_WIDTH || min_y >= LCD_HEIGHT)
    {
        return;
    }

    if (min_x < 0)
        min_x = 0;
    if (min_y < 0)
        min_y = 0;
    if (max_x >= LCD_WIDTH)
        max_x = LCD_WIDTH - 1;
    if (max_y >= LCD_HEIGHT)
        max_y = LCD_HEIGHT - 1;

    int32_t area = lcd_edge_function(x1, y1, x2, y2, x3, y3);
    if (area == 0)
    {
        lcd_draw_line(x1, y1, x2, y2, color);
        lcd_draw_line(x2, y2, x3, y3, color);
        lcd_draw_line(x3, y3, x1, y1, color);
        return;
    }

    uint8_t c = lcd_color565_to_332(color);
    for (int32_t py = min_y; py <= max_y; ++py)
    {
        for (int32_t px = min_x; px <= max_x; ++px)
        {
            int32_t w0 = lcd_edge_function(x2, y2, x3, y3, px, py);
            int32_t w1 = lcd_edge_function(x3, y3, x1, y1, px, py);
            int32_t w2 = lcd_edge_function(x1, y1, x2, y2, px, py);

            if ((area > 0 && w0 >= 0 && w1 >= 0 && w2 >= 0) ||
                (area < 0 && w0 <= 0 && w1 <= 0 && w2 <= 0))
            {
                s_framebuffer[lcd_framebuffer_index((uint16_t)px, (uint16_t)py)] = c;
            }
        }
    }
}

// Same scanline walk as lcd_fill_triangle, but each pixel is blended with what
// is already in the framebuffer instead of replacing it.
void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3,
                             uint16_t y3, uint16_t color, uint8_t alpha)
{
    if (alpha == 0 || s_framebuffer == NULL)
    {
        return;
    }

    if (alpha == 255)
    {
        lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
        return;
    }

    const uint8_t sr = (color >> 11) & 0x1F;
    const uint8_t sg = (color >> 5) & 0x3F;
    const uint8_t sb = color & 0x1F;
    const uint8_t inv_alpha = 255 - alpha;

    // Sort the vertices so y1 <= y2 <= y3.
    if (y1 > y2)
    {
        uint16_t t;
        t = x1; x1 = x2; x2 = t;
        t = y1; y1 = y2; y2 = t;
    }
    if (y1 > y3)
    {
        uint16_t t;
        t = x1; x1 = x3; x3 = t;
        t = y1; y1 = y3; y3 = t;
    }
    if (y2 > y3)
    {
        uint16_t t;
        t = x2; x2 = x3; x3 = t;
        t = y2; y2 = y3; y3 = t;
    }

    const int32_t total_h = (int32_t)y3 - (int32_t)y1;
    if (total_h == 0)
    {
        return;
    }

    for (int32_t i = 0; i < total_h; ++i)
    {
        const int32_t cur_y = (int32_t)y1 + i;
        if (cur_y < 0 || cur_y >= LCD_HEIGHT)
        {
            continue;
        }

        const bool second_half = (i > (int32_t)y2 - (int32_t)y1) || (y2 == y1);
        const int32_t seg_h = second_half ? (int32_t)y3 - (int32_t)y2 : (int32_t)y2 - (int32_t)y1;
        if (seg_h == 0)
        {
            continue;
        }

        const float t = (float)i / (float)total_h;
        const float beta = (float)(i - (second_half ? (int32_t)y2 - (int32_t)y1 : 0)) / (float)seg_h;

        int32_t ax = (int32_t)(x1 + (float)((int32_t)x3 - (int32_t)x1) * t);
        int32_t bx = second_half
                         ? (int32_t)(x2 + (float)((int32_t)x3 - (int32_t)x2) * beta)
                         : (int32_t)(x1 + (float)((int32_t)x2 - (int32_t)x1) * beta);

        if (ax > bx)
        {
            const int32_t tmp = ax;
            ax = bx;
            bx = tmp;
        }

        if (ax < 0)
        {
            ax = 0;
        }
        if (bx >= LCD_WIDTH)
        {
            bx = LCD_WIDTH - 1;
        }

        for (int32_t px = ax; px <= bx; ++px)
        {
            const size_t idx = lcd_framebuffer_index((uint16_t)px, (uint16_t)cur_y);

            // s_palette holds the RGB565 value byte-swapped ready for the SPI
            // transfer, so undo that before pulling the channels out of it.
            const uint16_t swapped = s_palette[s_framebuffer[idx]];
            const uint16_t dst_color = (uint16_t)((swapped >> 8) | (swapped << 8));

            const uint8_t dr = (dst_color >> 11) & 0x1F;
            const uint8_t dg = (dst_color >> 5) & 0x3F;
            const uint8_t db = dst_color & 0x1F;

            const uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
            const uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
            const uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

            const uint16_t blended = (uint16_t)(((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb);
            s_framebuffer[idx] = lcd_color565_to_332(blended);
        }
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3,
                       uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                              uint16_t radius, uint16_t color)
{
    (void)radius;
    lcd_fill_rect(x, y, width, height, color);
}

void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    if (s_framebuffer == NULL)
    {
        return;
    }

    lcd_set_font(size);
    const FontTable *font = lcd_get_font();
    uint8_t character = (uint8_t)c;
    if (character < 32 || character > 126)
    {
        character = '?';
    }

    uint8_t bytes_per_row = (uint8_t)((font->width + 7U) / 8U);
    size_t glyph_stride = (size_t)font->height * bytes_per_row;
    const uint8_t *glyph = &font->table[(size_t)(character - 32U) * glyph_stride];

    uint8_t c332 = lcd_color565_to_332(color);
    for (uint8_t row = 0; row < font->height; ++row)
    {
        if (y + row >= LCD_HEIGHT)
        {
            break;
        }

        for (uint8_t col = 0; col < font->width; ++col)
        {
            if (x + col >= LCD_WIDTH)
            {
                break;
            }

            uint8_t glyph_byte = glyph[(size_t)row * bytes_per_row + (col / 8U)];
            if ((glyph_byte & (uint8_t)(0x80U >> (col % 8U))) != 0)
            {
                s_framebuffer[lcd_framebuffer_index(x + col, y + row)] = c332;
            }
        }
    }
}

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    if (text == NULL)
    {
        return;
    }

    lcd_set_font(size);

    uint16_t cursor_x = x;
    uint16_t cursor_y = y;
    uint16_t start_x = x;

    for (const char *cursor = text; *cursor != '\0'; ++cursor)
    {
        if (*cursor == '\r')
        {
            continue;
        }

        if (*cursor == '\n')
        {
            cursor_x = start_x;
            cursor_y = (uint16_t)(cursor_y + lcd_line_advance());
            if (cursor_y >= LCD_HEIGHT)
            {
                break;
            }
            continue;
        }

        if ((uint32_t)cursor_x + lcd_get_font()->width > LCD_WIDTH)
        {
            cursor_x = start_x;
            cursor_y = (uint16_t)(cursor_y + lcd_line_advance());
        }

        if ((uint32_t)cursor_y + lcd_get_font()->height > LCD_HEIGHT)
        {
            break;
        }

        lcd_draw_char(cursor_x, cursor_y, *cursor, color, size);
        cursor_x = (uint16_t)(cursor_x + lcd_text_advance());
    }
}

uint8_t lcd_get_font_height(void)
{
    return lcd_get_font()->height;
}

uint8_t lcd_get_font_width(void)
{
    return lcd_get_font()->width;
}

void lcd_set_font(FontSize size)
{
    s_current_font = lcd_font_from_size(size);
}
