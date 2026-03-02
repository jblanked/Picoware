#include "auto_complete_mp.h"

const mp_obj_type_t auto_complete_mp_type;

void auto_complete_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "AutoComplete(");
    if (self->freed)
    {
        mp_print_str(print, "freed=True");
    }
    else
    {
        mp_print_str(print, "suggestion_count=");
        mp_obj_print_helper(print, mp_obj_new_int(self->context.suggestion_count), PRINT_REPR);
        mp_print_str(print, ", suggestions=[");
        for (uint8_t i = 0; i < self->context.suggestion_count; i++)
        {
            if (i > 0)
            {
                mp_print_str(print, ", ");
            }
            mp_obj_print_helper(print, mp_obj_new_str(self->context.suggestions[i], strlen(self->context.suggestions[i])), PRINT_REPR);
        }
        mp_print_str(print, "]");
    }
    mp_print_str(print, ")");
}

mp_obj_t auto_complete_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    auto_complete_mp_obj_t *self = mp_obj_malloc_with_finaliser(auto_complete_mp_obj_t, &auto_complete_mp_type);
    self->base.type = &auto_complete_mp_type;
    self->freed = false;
    // Initialize AutoComplete structure
    if (!auto_complete_init(&self->context))
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to initialize AutoComplete context"));
    }
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t auto_complete_mp_del(mp_obj_t self_in)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->freed)
    {
        auto_complete_free(&self->context);
        self->freed = true;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(auto_complete_mp_del_obj, auto_complete_mp_del);

void auto_complete_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_context && !self->freed)
        {
            mp_obj_t tuple[2]; // suggestions, suggestion_count
            mp_obj_t suggestions_tuple[self->context.suggestion_count];
            for (uint8_t i = 0; i < self->context.suggestion_count; i++)
            {
                suggestions_tuple[i] = mp_obj_new_str(self->context.suggestions[i], strlen(self->context.suggestions[i]));
            }
            tuple[0] = mp_obj_new_tuple(self->context.suggestion_count, suggestions_tuple);
            tuple[1] = mp_obj_new_int(self->context.suggestion_count);
            destination[0] = mp_obj_new_tuple(2, tuple);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&auto_complete_mp_del_obj);
        }
    }
}
mp_obj_t auto_complete_mp_add_word(mp_obj_t self_in, mp_obj_t word_obj)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->freed)
    {
        const char *word = mp_obj_str_get_str(word_obj);
        return auto_complete_add_word(&self->context, word) ? mp_const_true : mp_const_false;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_2(auto_complete_mp_add_word_obj, auto_complete_mp_add_word);

mp_obj_t auto_complete_mp_remove_suggestions(mp_obj_t self_in)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->freed)
    {
        auto_complete_remove_suggestions(&self->context);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(auto_complete_mp_remove_suggestions_obj, auto_complete_mp_remove_suggestions);

mp_obj_t auto_complete_mp_remove_words(mp_obj_t self_in)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->freed)
    {
        auto_complete_remove_words(&self->context);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(auto_complete_mp_remove_words_obj, auto_complete_mp_remove_words);

mp_obj_t auto_complete_mp_search(mp_obj_t self_in, mp_obj_t prefix_obj)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *prefix = mp_obj_str_get_str(prefix_obj);
    if (!self->freed && auto_complete_search(&self->context, prefix))
    {
        mp_obj_t tuple[self->context.suggestion_count];
        for (uint8_t i = 0; i < self->context.suggestion_count; i++)
        {
            tuple[i] = mp_obj_new_str(self->context.suggestions[i], strlen(self->context.suggestions[i]));
        }
        return mp_obj_new_tuple(self->context.suggestion_count, tuple);
    }
    else
    {
        return mp_const_none;
    }
}
static MP_DEFINE_CONST_FUN_OBJ_2(auto_complete_mp_search_obj, auto_complete_mp_search);

#if defined(STORAGE_INCLUDE) && defined(STORAGE_READ)
mp_obj_t auto_complete_mp_add_dictionary(mp_obj_t self_in, mp_obj_t filename_obj)
{
    auto_complete_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *filename = mp_obj_str_get_str(filename_obj);
    if (!self->freed && auto_complete_add_dictionary(&self->context, filename))
    {
        return mp_const_true;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_2(auto_complete_mp_add_dictionary_obj, auto_complete_mp_add_dictionary);
#endif

static const mp_rom_map_elem_t auto_complete_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_add_word), MP_ROM_PTR(&auto_complete_mp_add_word_obj)},
    {MP_ROM_QSTR(MP_QSTR_search), MP_ROM_PTR(&auto_complete_mp_search_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove_suggestions), MP_ROM_PTR(&auto_complete_mp_remove_suggestions_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove_words), MP_ROM_PTR(&auto_complete_mp_remove_words_obj)},
#if defined(STORAGE_INCLUDE) && defined(STORAGE_READ)
    {MP_ROM_QSTR(MP_QSTR_add_dictionary), MP_ROM_PTR(&auto_complete_mp_add_dictionary_obj)},
#endif
};
static MP_DEFINE_CONST_DICT(auto_complete_mp_locals_dict, auto_complete_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    auto_complete_mp_type,
    MP_QSTR_AutoComplete, // Name of the type in Python
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, auto_complete_mp_print,       // Print function
    make_new, auto_complete_mp_make_new, // constructor
    attr, auto_complete_mp_attr,         // attribute handler
    locals_dict, &auto_complete_mp_locals_dict);

// Define module globals
static const mp_rom_map_elem_t auto_complete_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_auto_complete)},
    {MP_ROM_QSTR(MP_QSTR_AutoComplete), MP_ROM_PTR(&auto_complete_mp_type)},
};
static MP_DEFINE_CONST_DICT(auto_complete_module_globals, auto_complete_module_globals_table);

// Define module
const mp_obj_module_t auto_complete_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&auto_complete_module_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_auto_complete, auto_complete_user_cmodule);