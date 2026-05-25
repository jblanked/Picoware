#pragma once

// memory info
#define MEMORY_INCLUDE "py/runtime.h"
#define MEMORY_ALLOC m_malloc
#define MEMORY_FREE m_free
#define MEMORY_REALLOC m_realloc

// storage info
#if defined(CARDPUTER)
#define STORAGE_INCLUDE "../cardputer/sd/storage.h"
#define STORAGE_READ storage_file_read
#define STORAGE_MAX_READ_SIZE 4096
#elif !defined(WAVESHARE_1_28) && !defined(CROWPANEL_10_1)
#define STORAGE_INCLUDE "storage.h"
#define STORAGE_READ storage_read
#define STORAGE_MAX_READ_SIZE 4096
#endif