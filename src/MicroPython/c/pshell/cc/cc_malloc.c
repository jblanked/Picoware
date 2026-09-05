#include <stdarg.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef DESKTOP
#if defined(__linux__) && defined(__x86_64__)
#include <sys/mman.h>
#endif
#endif

#include "py/runtime.h"

#include "cc.h"
#include "cc_malloc.h"

typedef struct qentry_s
{
    struct qentry_s *next;
#ifdef DESKTOP
    size_t allocation_size;
#endif
    char data[0];
} qentry_t;

#ifdef PSHELL_MICROPYTHON
#ifdef DESKTOP
#define UDATA
#else
#define UDATA __attribute__((section("ccudata")))
#endif
#else
#define UDATA __attribute__((section(".ccudata")))
#endif

static qentry_t malloc_list UDATA; // list of allocated memory blocks

#ifdef DESKTOP
// The compiler stores AST links in signed 32-bit integers. Keep Desktop
// allocations representable until those internal pointer fields are widened.
static qentry_t *desktop_alloc(size_t allocation_size)
{
#if defined(__linux__) && defined(__x86_64__) && defined(MAP_32BIT)
    void *memory = mmap(NULL, allocation_size, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    if (memory == MAP_FAILED)
        return NULL;
    if ((uintptr_t)memory > INT_MAX)
    {
        munmap(memory, allocation_size);
        return NULL;
    }
    return memory;
#else
    qentry_t *memory = m_malloc(allocation_size);
    if (memory && (uintptr_t)memory > INT_MAX)
    {
        m_free(memory);
        memory = NULL;
    }
    return memory;
#endif
}
#endif

// local memory management functions
void *cc_malloc(int l, int cc, int zero)
{
    size_t allocation_size = l + sizeof(qentry_t);
#ifdef DESKTOP
    qentry_t *p = desktop_alloc(allocation_size);
#else
    qentry_t *p = m_malloc(allocation_size);
#endif
    if (!p)
    {
        if (cc)
            run_fatal("out of memory");
        else
            return 0;
    }
#ifdef DESKTOP
    p->allocation_size = allocation_size;
#endif
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
#ifdef DESKTOP
#if defined(__linux__) && defined(__x86_64__) && defined(MAP_32BIT)
            munmap(p2, p2->allocation_size);
#else
            m_free(p2);
#endif
#else
            m_free(p2);
#endif
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
#ifdef DESKTOP
#if defined(__linux__) && defined(__x86_64__) && defined(MAP_32BIT)
        munmap(p, p->allocation_size);
#else
        m_free(p);
#endif
#else
        m_free(p);
#endif
    }
}
