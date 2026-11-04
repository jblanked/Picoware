#include "array_buf.h"
#include <string.h>
#include "py/runtime.h"
#include "py/gc.h"

#define ARRAY_BUF_MAGIC 0xAB

struct array_buf_hdr
{
    uint8_t magic;   // magic marker for type identification
    const void *ptr; // pointer to the buffer data
    size_t len;      // length of the buffer in bytes
};

mjs_val_t mjs_mk_array_buf(struct mjs *mjs, const void *ptr, size_t len)
{
    struct array_buf_hdr *hdr = (struct array_buf_hdr *)m_malloc0(sizeof(*hdr));
    if (hdr == NULL)
    {
        return MJS_UNDEFINED;
    }
    hdr->magic = ARRAY_BUF_MAGIC;
    hdr->ptr = ptr;
    hdr->len = len;
    return mjs_mk_foreign(mjs, hdr);
}

int mjs_is_array_buf(mjs_val_t v)
{
    if ((v & MJS_TAG_MASK) != MJS_TAG_FOREIGN)
    {
        return 0;
    }
    void *ptr = (void *)(uintptr_t)(v & 0xFFFFFFFFFFFFUL);
    if (gc_nbytes(ptr) < sizeof(struct array_buf_hdr))
    {
        return 0;
    }
    struct array_buf_hdr *hdr = (struct array_buf_hdr *)ptr;
    return hdr->magic == ARRAY_BUF_MAGIC;
}

const void *mjs_array_buf_get_ptr(struct mjs *mjs, mjs_val_t v, size_t *len)
{
    (void)mjs;
    if (!mjs_is_array_buf(v))
    {
        if (len)
            *len = 0;
        return NULL;
    }
    struct array_buf_hdr *hdr = (struct array_buf_hdr *)(uintptr_t)(v & 0xFFFFFFFFFFFFUL);
    if (len)
        *len = hdr->len;
    return hdr->ptr;
}
