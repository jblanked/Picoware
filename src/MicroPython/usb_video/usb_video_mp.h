/*
MicroPython C module for streaming LCD framebuffer over USB CDC.
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once
#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"

#ifdef __cplusplus
extern "C"
{
#endif

    // Wire format (all multi-byte fields are little-endian):
    //   Offset  Size  Field
    //   0       4     Magic "PICV" (0x50494356)
    //   4       2     Width  (pixels)
    //   6       2     Height (pixels)
    //   8       2     Pixel format (0=RGB332, 1=RGB565)
    //   10      ?     Pixel rows, top-to-bottom

#define USB_VIDEO_MAGIC 0x50494356
#define USB_VIDEO_HDR_SIZE 10
#define USB_VIDEO_FORMAT_RGB332 0
#define USB_VIDEO_FORMAT_RGB565 1

    typedef struct
    {
        mp_obj_base_t base;
        bool active;
        uint8_t pixel_format;
    } usb_video_stream_obj_t;

    extern const mp_obj_type_t usb_video_stream_type;

    void usb_video_set_swap_callback(bool (*cb)(void));

    void usb_video_stream_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the USBVideoStream object
    mp_obj_t usb_video_stream_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the USBVideoStream object
    mp_obj_t usb_video_stream_mp_del(mp_obj_t self_in);                                                                 // destructor for the USBVideoStream object
    void usb_video_stream_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the USBVideoStream object

    mp_obj_t usb_video_stream_mp_start(mp_obj_t self_in);
    mp_obj_t usb_video_stream_mp_stop(mp_obj_t self_in);
    mp_obj_t usb_video_stream_mp_send_frame(mp_obj_t self_in);

#ifdef __cplusplus
}
#endif
