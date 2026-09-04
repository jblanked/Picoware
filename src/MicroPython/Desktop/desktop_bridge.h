#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

void desktop_lcd_clear(uint16_t color);
void desktop_lcd_pixel(uint16_t x, uint16_t y, uint16_t color);
void desktop_lcd_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                      uint16_t color);
void desktop_lcd_char(uint16_t x, uint16_t y, char character, uint16_t color,
                      int font_size);
void desktop_lcd_triangle(uint16_t x1, uint16_t y1, uint16_t x2,
                          uint16_t y2, uint16_t x3, uint16_t y3,
                          uint16_t color);
void desktop_lcd_rectangle(uint16_t x, uint16_t y, uint16_t width,
                           uint16_t height, uint16_t color);
void desktop_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                uint16_t height, uint16_t color);
void desktop_lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                      uint16_t height, uint16_t radius,
                                      uint16_t color);
void desktop_lcd_circle(uint16_t x, uint16_t y, uint16_t radius,
                        uint16_t color);
void desktop_lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius,
                             uint16_t color);
void desktop_lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2,
                               uint16_t y2, uint16_t x3, uint16_t y3,
                               uint16_t color);
void desktop_lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2,
                                     uint16_t y2, uint16_t x3, uint16_t y3,
                                     uint16_t color, uint8_t alpha);
void desktop_lcd_read_row(uint16_t row, uint8_t *out_buffer);
void desktop_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                      const void *buffer);
void desktop_lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width,
                            uint16_t height, const void *buffer);
void desktop_lcd_text(uint16_t x, uint16_t y, const char *text,
                      uint16_t color, int font_size);
void desktop_lcd_set_brightness(uint8_t brightness);
void desktop_lcd_set_rgb_led(uint8_t red, uint8_t green, uint8_t blue);
void desktop_lcd_swap(void);

void desktop_log_message(const char *message);
size_t desktop_storage_file_size(const char *path);
size_t desktop_storage_file_read(const char *path, void *buffer,
                                 size_t buffer_size);
size_t desktop_storage_file_read_chunk(const char *path, void *buffer,
                                       size_t buffer_size, size_t offset);
bool desktop_storage_file_write(const char *path, const void *buffer,
                                size_t buffer_size);
void *desktop_storage_file_write_open(const char *path);
void desktop_storage_file_close(void *handle);
bool desktop_storage_file_write_file_chunk(void *handle, const void *data,
                                           size_t size);

bool desktop_http_get_response(void *buffer, size_t buffer_size);
bool desktop_http_is_finished(void);
bool desktop_http_send_request(const char *url, const char *method,
                               const char *headers, const char *payload);
bool desktop_http_get_websocket_response(void *buffer, size_t buffer_size);
bool desktop_http_websocket_is_connected(void);
bool desktop_http_websocket_send(const char *message);
bool desktop_http_websocket_start(const char *url, int port);
bool desktop_http_websocket_stop(void);
