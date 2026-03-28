/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "picoware_lvgl.h"

    typedef struct
    {
        mp_obj_base_t base;
        int y;
        int height;
        uint16_t text_color_565;
        uint16_t background_color_565;
        uint16_t selected_color_565;
        uint16_t border_color_565;
        int border_width;
        int selected_index;
        mp_obj_t *items;
        size_t item_count;
        size_t item_capacity;
        bool is_circular;
        lv_obj_t *screen;
        lv_obj_t *container;
        lv_obj_t *title_label;
        lv_obj_t *list_widget;
        lv_obj_t **list_buttons; // Array of button pointers
        bool freed;
    } picoware_lvgl_list_obj_t;

    extern const mp_obj_type_t picoware_lvgl_list_type;

    void picoware_lvgl_list_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the List object
    mp_obj_t picoware_lvgl_list_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // List constructor
    mp_obj_t picoware_lvgl_list_del(mp_obj_t self_in);                                                                 // List destructor
    void picoware_lvgl_list_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // List attribute handler
    mp_obj_t picoware_lvgl_list_clear(mp_obj_t self_in);                                                               // List.clear() - Clear the list
    mp_obj_t picoware_lvgl_list_add_item(mp_obj_t self_in, mp_obj_t item_in);                                          // List.add_item(item) - Add an item to the list
    mp_obj_t picoware_lvgl_list_remove_item(mp_obj_t self_in, mp_obj_t index_in);                                      // List.remove_item(index) - Remove an item from the list
    mp_obj_t picoware_lvgl_list_get_item(mp_obj_t self_in, mp_obj_t index_in);                                         // List.get_item(index) - Get an item from the list
    mp_obj_t picoware_lvgl_list_item_exists(mp_obj_t self_in, mp_obj_t item_in);                                       // List.item_exists(item) - Check if an item exists in the list
    mp_obj_t picoware_lvgl_list_set_selected(mp_obj_t self_in, mp_obj_t index_in);                                     // List.set_selected(index) - Set the selected item
    mp_obj_t picoware_lvgl_list_scroll_up(mp_obj_t self_in);                                                           // List.scroll_up() - Scroll up
    mp_obj_t picoware_lvgl_list_set_title(mp_obj_t self_in, mp_obj_t title_in);                                        // List.set_title(title) - Set the title
    mp_obj_t picoware_lvgl_list_scroll_down(mp_obj_t self_in);                                                         // List.scroll_down() - Scroll down
    mp_obj_t picoware_lvgl_list_draw(mp_obj_t self_in);                                                                // List.draw() - Draw the list
    mp_obj_t picoware_lvgl_list_current_item(mp_obj_t self_in);
    mp_obj_t picoware_lvgl_list_item_count_prop(mp_obj_t self_in);
    mp_obj_t picoware_lvgl_list_selected_index_prop(mp_obj_t self_in);
    mp_obj_t picoware_lvgl_list_list_height_prop(mp_obj_t self_in);

#ifdef __cplusplus
}
#endif
