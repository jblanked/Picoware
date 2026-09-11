#include "compat.hpp"
#include "../../../ghouls/ghouls_mp.h"

// Reuse the firmware binding, substituting only Desktop attribute dispatch.
// A function-like macro renames its definition but leaves the type's function
// pointer targeting the adapter declared above.
#define ghouls_mp_attr(...) desktop_ghouls_original_attr(__VA_ARGS__)
#include "../../../ghouls/ghouls_mp.cpp"
#undef ghouls_mp_attr

void ghouls_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    if (destination[0] != MP_OBJ_NULL)
        return;
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (attribute == MP_QSTR___del__)
    {
        destination[0] = MP_OBJ_FROM_PTR(&ghouls_mp_del_obj);
        destination[1] = self_in;
    }
    else if (attribute == MP_QSTR_is_active && self->freed)
        destination[0] = mp_const_false;
    else if (attribute == MP_QSTR_is_active)
        desktop_ghouls_original_attr(self_in, attribute, destination);
    else
        destination[1] = MP_OBJ_SENTINEL;
}
