#include "font_mp.h"

const mp_obj_type_t font_mp_type;
const mp_obj_type_t font_size_mp_type;

const uint8_t *font_get_character(FontSize size, char c)
{
  const uint8_t *font_data = font_get_data(size);
  if (font_data == NULL)
  {
    return NULL; // Invalid font size
  }

  // Each character is stored as rows, with bytes per row determined by width
  uint8_t char_width = font_get_width(size);
  uint8_t char_height = font_get_height(size);
  uint8_t bytes_per_row = (char_width + 7) / 8;          // Bytes needed per row
  uint16_t bytes_per_char = bytes_per_row * char_height; // Total bytes per character

  // Calculate the index of the character in the font data (assuming ASCII)
  if (c < 32 || c > 126)
  {
    return NULL; // Character out of range
  }
  uint16_t char_index = (c - 32) * bytes_per_char;

  return &font_data[char_index]; // Return pointer to the character bitmap data
}

const uint8_t *font_get_data(FontSize size)
{
  switch (size)
  {
  case FONT_XTRA_SMALL:
    return Font8.table;
  case FONT_SMALL:
    return Font12.table;
  case FONT_MEDIUM:
    return Font16.table;
  case FONT_LARGE:
    return Font20.table;
  case FONT_XTRA_LARGE:
    return Font24.table;
  default:
    return Font8.table;
  }
}

FontTable font_get_table(FontSize size)
{
  switch (size)
  {
  case FONT_XTRA_SMALL:
    return Font8;
  case FONT_SMALL:
    return Font12;
  case FONT_MEDIUM:
    return Font16;
  case FONT_LARGE:
    return Font20;
  case FONT_XTRA_LARGE:
    return Font24;
  default:
    return Font8;
  }
}

uint8_t font_get_height(FontSize size)
{
  switch (size)
  {
  case FONT_XTRA_SMALL:
    return Font8.height;
  case FONT_SMALL:
    return Font12.height;
  case FONT_MEDIUM:
    return Font16.height;
  case FONT_LARGE:
    return Font20.height;
  case FONT_XTRA_LARGE:
    return Font24.height;
  default:
    return Font8.height;
  }
}

uint8_t font_get_width(FontSize size)
{
  switch (size)
  {
  case FONT_XTRA_SMALL:
    return Font8.width;
  case FONT_SMALL:
    return Font12.width;
  case FONT_MEDIUM:
    return Font16.width;
  case FONT_LARGE:
    return Font20.width;
  case FONT_XTRA_LARGE:
    return Font24.width;
  default:
    return Font8.width;
  }
}

mp_obj_t font_mp_get_character(mp_obj_t self_in, mp_obj_t size, mp_obj_t char_obj)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (!self->initialized)
  {
    return mp_const_none; // Font not initialized
  }
  char c = mp_obj_get_int(char_obj);
  FontSize font_size = mp_obj_get_int(size);
  const uint8_t *char_data = font_get_character(font_size, c);
  if (char_data == NULL)
  {
    return mp_const_none; // Character not found or invalid font size
  }
  FontTable table = font_get_table(font_size);
  return mp_obj_new_bytes(char_data, (table.width * table.height + 7) / 8); // Return the character bitmap as bytes
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(font_mp_get_character_obj, font_mp_get_character);

mp_obj_t font_mp_get_data(mp_obj_t self_in, mp_obj_t size)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (!self->initialized)
  {
    return mp_const_none; // Font not initialized
  }
  FontSize font_size = mp_obj_get_int(size);
  FontTable table = font_get_table(font_size);
  return mp_obj_new_bytes(table.table, (table.width * table.height + 7) / 8 * (126 - 32 + 1)); // Return the entire font data as bytes
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(font_mp_get_data_obj, font_mp_get_data);

mp_obj_t font_mp_get_height(mp_obj_t self_in, mp_obj_t size)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (!self->initialized)
  {
    return mp_const_none; // Font not initialized
  }
  FontSize font_size = mp_obj_get_int(size);
  uint8_t height = font_get_height(font_size);
  return mp_obj_new_int(height); // Return the height of the font in pixels
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(font_mp_get_height_obj, font_mp_get_height);

mp_obj_t font_mp_get_width(mp_obj_t self_in, mp_obj_t size)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (!self->initialized)
  {
    return mp_const_none; // Font not initialized
  }
  FontSize font_size = mp_obj_get_int(size);
  uint8_t width = font_get_width(font_size);
  return mp_obj_new_int(width); // Return the width of the font in pixels
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(font_mp_get_width_obj, font_mp_get_width);

void font_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
  (void)kind; // Unused parameter
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  mp_print_str(print, "Font(initialized=");
  mp_print_str(print, self->initialized ? "True" : "False");
  mp_print_str(print, ")");
}
mp_obj_t font_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
  font_mp_obj_t *self = mp_obj_malloc_with_finaliser(font_mp_obj_t, &font_mp_type);
  self->base.type = &font_mp_type;
  self->initialized = true;
  return MP_OBJ_FROM_PTR(self);
}

mp_obj_t font_mp_del(mp_obj_t self_in)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  self->initialized = false; // Mark the font as uninitialized
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(font_mp_del_obj, font_mp_del);

void font_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
  font_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (destination[0] == MP_OBJ_NULL)
  {
    // Getting an attribute
    if (attribute == MP_QSTR_initialized)
    {
      destination[0] = mp_obj_new_bool(self->initialized);
    }
    else if (attribute == MP_QSTR___del__)
    {
      destination[0] = MP_OBJ_FROM_PTR(&font_mp_del_obj);
    }
  }
}

STATIC const mp_rom_map_elem_t font_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_character), MP_ROM_PTR(&font_mp_get_character_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_data), MP_ROM_PTR(&font_mp_get_data_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_height), MP_ROM_PTR(&font_mp_get_height_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_width), MP_ROM_PTR(&font_mp_get_width_obj)},
};
STATIC MP_DEFINE_CONST_DICT(font_mp_locals_dict, font_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    font_mp_type,
    MP_QSTR_Font,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, font_mp_print,
    make_new, font_mp_make_new,
    attr, font_mp_attr,
    locals_dict, &font_mp_locals_dict);

void font_size_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
  (void)kind; // Unused parameter
  font_size_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  mp_print_str(print, "FontSize(size=");
  switch (self->size)
  {
  case FONT_XTRA_SMALL:
    mp_print_str(print, "FONT_XTRA_SMALL");
    break;
  case FONT_SMALL:
    mp_print_str(print, "FONT_SMALL");
    break;
  case FONT_MEDIUM:
    mp_print_str(print, "FONT_MEDIUM");
    break;
  case FONT_LARGE:
    mp_print_str(print, "FONT_LARGE");
    break;
  case FONT_XTRA_LARGE:
    mp_print_str(print, "FONT_XTRA_LARGE");
    break;
  default:
    mp_print_str(print, "UNKNOWN");
    break;
  };
  mp_print_str(print, ", width=");
  mp_obj_print_helper(print, mp_obj_new_int(self->width), PRINT_REPR);
  mp_print_str(print, ", height=");
  mp_obj_print_helper(print, mp_obj_new_int(self->height), PRINT_REPR);
  mp_print_str(print, ")");
}

mp_obj_t font_size_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
  font_size_mp_obj_t *self = mp_obj_malloc_with_finaliser(font_size_mp_obj_t, &font_size_mp_type);
  self->base.type = &font_size_mp_type;
  if (n_args == 1)
  {
    FontSize size = mp_obj_get_int(args[0]);
    self->size = size;
    self->width = font_get_width(size);
    self->height = font_get_height(size);
  }
  else
  {
    self->size = FONT_DEFAULT;
    self->width = font_get_width(FONT_DEFAULT);
    self->height = font_get_height(FONT_DEFAULT);
  }
  return MP_OBJ_FROM_PTR(self);
}

mp_obj_t font_size_mp_del(mp_obj_t self_in)
{
  font_size_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  self->size = FONT_DEFAULT;
  self->width = 0;
  self->height = 0;
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(font_size_mp_del_obj, font_size_mp_del);

void font_size_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
  font_size_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
  if (destination[0] == MP_OBJ_NULL)
  {
    // Getting an attribute
    if (attribute == MP_QSTR_size)
    {
      destination[0] = mp_obj_new_int(self->size);
    }
    else if (attribute == MP_QSTR_width)
    {
      destination[0] = mp_obj_new_int(self->width);
    }
    else if (attribute == MP_QSTR_height)
    {
      destination[0] = mp_obj_new_int(self->height);
    }
    else if (attribute == MP_QSTR___del__)
    {
      destination[0] = MP_OBJ_FROM_PTR(&font_size_mp_del_obj);
    }
  }
  else if (destination[1] != MP_OBJ_NULL)
  {
    // Setting an attribute
    if (attribute == MP_QSTR_size)
    {
      FontSize new_size = mp_obj_get_int(destination[1]);
      self->size = new_size;
      self->width = font_get_width(new_size);
      self->height = font_get_height(new_size);
      destination[0] = MP_OBJ_NULL; // Indicate that the attribute was set successfully
    }
  }
}

MP_DEFINE_CONST_OBJ_TYPE(
    font_size_mp_type,
    MP_QSTR_FontSize,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, font_size_mp_print,
    make_new, font_size_mp_make_new,
    attr, font_size_mp_attr);

// Define module globals
STATIC const mp_rom_map_elem_t font_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_font)},
    {MP_ROM_QSTR(MP_QSTR_Font), MP_ROM_PTR(&font_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_FontSize), MP_ROM_PTR(&font_size_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(font_mp_globals, font_mp_globals_table);

// Define module
const mp_obj_module_t font_mp_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&font_mp_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_font, font_mp_user_cmodule);