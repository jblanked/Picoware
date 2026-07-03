/*
MicroPython C module for streaming LCD framebuffer over USB CDC.
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#include "usb_video_mp.h"
#include "../lcd/lcd_mp.h"
#include "lcd_config.h"

#include LCD_INCLUDE
#include "tusb.h"
#include "shared/tinyusb/mp_usbd_cdc.h"
#include "shared/tinyusb/mp_usbd.h"

#ifndef USB_VIDEO_ROWS_PER_CHUNK
#define USB_VIDEO_ROWS_PER_CHUNK 16
#endif

const mp_obj_type_t usb_video_stream_type;

void usb_video_set_swap_callback(bool (*cb)(void))
{
    lcd_mp_set_usb_video_callback(cb);
}

static bool _send_frame(void)
{
#ifndef LCD_MP_READ_ROW
    return false;
#endif
#if !defined(LCD_MP_WIDTH) || !defined(LCD_MP_HEIGHT)
    return false;
#endif
    if (!tud_cdc_connected())
    {
        return false;
    }

    uint16_t w = LCD_MP_WIDTH;
    uint16_t h = LCD_MP_HEIGHT;

    // Send header
    uint8_t hdr[USB_VIDEO_HDR_SIZE];
    hdr[0] = (uint8_t)(USB_VIDEO_MAGIC >> 0);
    hdr[1] = (uint8_t)(USB_VIDEO_MAGIC >> 8);
    hdr[2] = (uint8_t)(USB_VIDEO_MAGIC >> 16);
    hdr[3] = (uint8_t)(USB_VIDEO_MAGIC >> 24);
    hdr[4] = (uint8_t)(w >> 0);
    hdr[5] = (uint8_t)(w >> 8);
    hdr[6] = (uint8_t)(h >> 0);
    hdr[7] = (uint8_t)(h >> 8);
    hdr[8] = USB_VIDEO_FORMAT_RGB332;
    hdr[9] = 0;
    mp_usbd_cdc_tx_strn((const char *)hdr, USB_VIDEO_HDR_SIZE);
    mp_usbd_task();

    // Stream pixel rows, drain FIFO after each chunk
    uint8_t chunk[USB_VIDEO_ROWS_PER_CHUNK * LCD_MP_WIDTH];
    for (uint16_t ry = 0; ry < h; ry += USB_VIDEO_ROWS_PER_CHUNK)
    {
        uint16_t rows = (h - ry < USB_VIDEO_ROWS_PER_CHUNK) ? (h - ry) : USB_VIDEO_ROWS_PER_CHUNK;
        for (uint16_t r = 0; r < rows; r++)
        {
            LCD_MP_READ_ROW(ry + r, chunk + r * w);
        }
        mp_usbd_cdc_tx_strn((const char *)chunk, (uint32_t)rows * w);
        mp_usbd_task();
    }
    return true;
}

void usb_video_stream_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "USBVideoStream(");
    mp_print_str(print, "active=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->active), PRINT_REPR);
    mp_print_str(print, ", pixel_format=");
    mp_obj_print_helper(print, mp_obj_new_int(self->pixel_format), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t usb_video_stream_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 2, false);
#if defined(CARDPUTER) || defined(CROWPANEL_10_1)
    // let gc handle cleanup
    usb_video_stream_obj_t *self = mp_obj_malloc(usb_video_stream_obj_t, &usb_video_stream_type);
#else
    usb_video_stream_obj_t *self = mp_obj_malloc_with_finaliser(usb_video_stream_obj_t, &usb_video_stream_type);
#endif
    self->base.type = &usb_video_stream_type;
    self->active = false;
    self->pixel_format = USB_VIDEO_FORMAT_RGB332;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t usb_video_stream_mp_del(mp_obj_t self_in)
{
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->active)
    {
        self->active = false;
        usb_video_set_swap_callback(NULL);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(usb_video_stream_del_obj, usb_video_stream_mp_del);

void usb_video_stream_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attribute
        switch (attribute)
        {
        case MP_QSTR_active:
            destination[0] = mp_obj_new_bool(self->active);
            break;
        case MP_QSTR_pixel_format:
            destination[0] = mp_obj_new_int(self->pixel_format);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&usb_video_stream_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL; // not found here; fall through to locals_dict
            break;
        };
    }
}

mp_obj_t usb_video_stream_mp_start(mp_obj_t self_in)
{
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->active)
    {
        self->active = true;
        usb_video_set_swap_callback(_send_frame);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(usb_video_stream_start_obj, usb_video_stream_mp_start);

mp_obj_t usb_video_stream_mp_stop(mp_obj_t self_in)
{
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->active)
    {
        self->active = false;
        usb_video_set_swap_callback(NULL);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(usb_video_stream_stop_obj, usb_video_stream_mp_stop);

mp_obj_t usb_video_stream_mp_send_frame(mp_obj_t self_in)
{
    usb_video_stream_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return self->active && _send_frame() ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(usb_video_stream_send_frame_obj, usb_video_stream_mp_send_frame);

static const mp_rom_map_elem_t usb_video_stream_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&usb_video_stream_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&usb_video_stream_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR_send_frame), MP_ROM_PTR(&usb_video_stream_send_frame_obj)},
};
static MP_DEFINE_CONST_DICT(usb_video_stream_locals_dict, usb_video_stream_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    usb_video_stream_type,
    MP_QSTR_USBVideoStream,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, usb_video_stream_mp_print,
    make_new, usb_video_stream_mp_make_new,
    attr, usb_video_stream_mp_attr,
    locals_dict, &usb_video_stream_locals_dict);

static const mp_rom_map_elem_t usb_video_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_usb_video_mp)},
    {MP_ROM_QSTR(MP_QSTR_USBVideoStream), MP_ROM_PTR(&usb_video_stream_type)},
};
static MP_DEFINE_CONST_DICT(usb_video_module_globals, usb_video_module_globals_table);

const mp_obj_module_t usb_video_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&usb_video_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_usb_video_mp, usb_video_module);
