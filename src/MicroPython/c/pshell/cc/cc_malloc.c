#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include <pico/stdlib.h>
#include "py/runtime.h"

#include "cc.h"
#include "cc_malloc.h"

typedef struct qentry_s
{
    struct qentry_s *next;
    char data[0];
} qentry_t;

#ifdef PSHELL_MICROPYTHON
#define UDATA __attribute__((section("ccudata")))
#else
#define UDATA __attribute__((section(".ccudata")))
#endif

static qentry_t malloc_list UDATA; // list of allocated memory blocks

// local memory management functions
void *cc_malloc(int l, int cc, int zero)
{
    qentry_t *p = m_malloc(l + sizeof(qentry_t));
    if (!p)
    {
        if (cc)
            run_fatal("out of memory");
        else
            return 0;
    }
    if (zero)
        memset(p->data, 0, l);
    p->next = malloc_list.next;
    malloc_list.next = p;
    return p->data;
}

void cc_free(void *p, int user)
{
    if (!p)
    {
        if (user)
            run_fatal("freeing a NULL pointer");
        else
            fatal("freeing a NULL pointer");
    }
    qentry_t *p2 = (qentry_t *)p - 1;
    qentry_t *last = &malloc_list;
    qentry_t *p3 = malloc_list.next;
    while (p3)
    {
        if (p2 == p3)
        {
            last->next = p2->next;
            m_free(p2);
            return;
        }
        last = p3;
        p3 = p3->next;
    }
    if (user)
        run_fatal("corrupted memory");
    else
        fatal("corrupted memory");
}

void cc_free_all(void)
{
    while (malloc_list.next)
    {
        qentry_t *p = malloc_list.next;
        malloc_list.next = p->next;
        m_free(p);
    }
}
