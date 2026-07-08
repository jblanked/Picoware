#include "storage.h"
#include <string.h>
#include "py/runtime.h"
#include "array_buf.h"
#include "../../sd/storage.h"

static char *storage_get_string(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t t_arg = mjs_arg(mjs, arg);
    if (!mjs_is_undefined(t_arg) && !mjs_is_null(t_arg))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &t_arg, &len);
        if (str != NULL)
        {
            char *copy = (char *)m_malloc(len + 1);
            if (copy)
            {
                memcpy(copy, str, len);
                copy[len] = '\0';
                return copy;
            }
            else
            {
                mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "Failed to allocate buffer for string copy");
            }
        }
    }
    return NULL;
}

void storage_read(struct mjs *mjs)
{
    char *filename_copy = storage_get_string(mjs, 0);
    const char *filename = filename_copy ? filename_copy : "";
    const size_t file_size = storage_file_size(filename);
    char *buffer = (char *)m_malloc(file_size);
    if (buffer == NULL)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "Failed to allocate buffer for file read");
        mjs_return(mjs, MJS_UNDEFINED);
        m_free(filename_copy);
        return;
    }
    const size_t bytes_read = storage_file_read(filename, buffer, file_size);
    mjs_return(mjs, mjs_mk_string(mjs, buffer, bytes_read, 1));
    m_free(filename_copy);
    m_free(buffer);
}

void storage_read_chunk(struct mjs *mjs)
{
    char *filename_copy = storage_get_string(mjs, 0);
    const char *filename = filename_copy ? filename_copy : "";
    const size_t offset = (size_t)mjs_get_int(mjs, mjs_arg(mjs, 1));
    const size_t chunk_size = (size_t)mjs_get_int(mjs, mjs_arg(mjs, 2));
    char *buffer = (char *)m_malloc(chunk_size);
    if (buffer == NULL)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "Failed to allocate buffer for file read");
        mjs_return(mjs, MJS_UNDEFINED);
        m_free(filename_copy);
        return;
    }
    const size_t bytes_read = storage_file_read(filename, buffer + offset, chunk_size);
    mjs_return(mjs, mjs_mk_string(mjs, buffer + offset, bytes_read, 1));
    m_free(filename_copy);
    m_free(buffer);
}

void storage_size(struct mjs *mjs)
{
    char *filename_copy = storage_get_string(mjs, 0);
    const char *filename = filename_copy ? filename_copy : "";
    const size_t file_size = storage_file_size(filename);
    mjs_return(mjs, mjs_mk_number(mjs, file_size));
    m_free(filename_copy);
}

void storage_write(struct mjs *mjs)
{
    char *filename_copy = storage_get_string(mjs, 0);
    const char *filename = filename_copy ? filename_copy : "";
    mjs_val_t data = mjs_arg(mjs, 1);
    const void *buf;
    size_t len;
    if (mjs_is_string(data))
    {
        buf = mjs_get_string(mjs, &data, &len);
    }
    else if (mjs_is_array_buf(data))
    {
        buf = mjs_array_buf_get_ptr(mjs, data, &len);
    }
    else
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 1: expected string or ArrayBuffer");
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        m_free(filename_copy);
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, storage_file_write(filename, buf, len)));
    m_free(filename_copy);
}

void storage_create(struct mjs *mjs, mjs_val_t *storage_obj)
{
    *storage_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *storage_obj, "read", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)storage_read));
    mjs_set(mjs, *storage_obj, "readChunk", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)storage_read_chunk));
    mjs_set(mjs, *storage_obj, "size", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)storage_size));
    mjs_set(mjs, *storage_obj, "write", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)storage_write));
}
