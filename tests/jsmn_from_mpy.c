#include "py/obj.h"
#include "py/runtime.h"
#include "py/nlr.h"

// lets try to call our same jsmn module but from python
void jsmn_test(void)
{
    nlr_buf_t nlr;

    if (nlr_push(&nlr) == 0)
    {
        // JSMN_LOG_INFO("Running jsmn_test...\n");
        //  --- 1. Import jsmn ---
        mp_obj_t jsmn = mp_import_name(
            MP_QSTR_jsmn,
            mp_const_none,
            MP_OBJ_NEW_SMALL_INT(0));

        // JSMN_LOG_INFO("jsmn module imported successfully.\n");

        // --- 2. Get the .value() function ---
        mp_obj_t get_func = mp_load_attr(jsmn, MP_QSTR_value);

        // JSMN_LOG_INFO("jsmn.value function loaded successfully.\n");

        // --- 3. Build the arguments ---
        mp_obj_t args[2];
        char data[] = "{\"key\": \"value\"}";
        args[0] = mp_obj_new_str("key", strlen("key")); // key
        args[1] = mp_obj_new_str(data, strlen(data));   // json string

        // JSMN_LOG_INFO("Arguments prepared: key='key', json_str='{ \"key\": \"value\" }'\n");

        // --- 4. Call jsmn.value(key, json_string) ---
        mp_obj_t key_value = mp_call_function_n_kw(get_func, 2, 0, args);

        // JSMN_LOG_INFO("jsmn.value function called successfully.\n");

        // --- 5. Print the result ---
        const char *key_value_str = mp_obj_str_get_str(key_value);
        printf("Value for 'key': %s\n", key_value_str);
        // JSMN_LOG_INFO("Value for 'key': %s\n", key_value_str);
        nlr_pop();
    }
    else
    {
        // Handle the exception (if any)
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
    }
}