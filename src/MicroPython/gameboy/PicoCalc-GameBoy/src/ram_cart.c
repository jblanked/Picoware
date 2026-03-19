#include "ram_cart.h"
#include "shared.h"

#include SD_INCLUDE
#include BUFFER_INCLUDE

#define WALNUT_GB_HEADER_ONLY
#ifndef WALNUT_GB_H
#include "walnut_cgb.h"
#endif

#define RAM_CART_CHUNK_SIZE 256

void read_cart_ram_file(struct gb_s *gb)
{
    char filename[16];
    size_t save_size = 0;
    gb_get_rom_name(gb, filename);
    gb_get_save_size_s(gb, &save_size);
    if (save_size > 0)
    {
        uint8_t chunk[RAM_CART_CHUNK_SIZE];
        void *fh = SD_FILE_OPEN(filename);
        if (fh)
        {
            uint32_t offset = 0;
            while (offset < save_size)
            {
                uint32_t len = save_size - offset;
                if (len > RAM_CART_CHUNK_SIZE)
                    len = RAM_CART_CHUNK_SIZE;
                size_t read = SD_FILE_READ_FILE_CHUNK(fh, chunk, len);
                if (read == 0)
                    break;
                BUFFER_RAM_BUFFER_WRITE(offset, chunk, (uint32_t)read);
                offset += (uint32_t)read;
            }
            SD_FILE_CLOSE(fh);
        }
        DBG_INFO("I read_cart_ram_file(%s) COMPLETE (%lu bytes)\n", filename, save_size);
    }
    else
    {
        DBG_INFO("I read_cart_ram_file(%s) SKIPPED\n", filename);
    }
}

void write_cart_ram_file(struct gb_s *gb)
{
    char filename[16];
    size_t save_size = 0;
    gb_get_rom_name(gb, filename);
    gb_get_save_size_s(gb, &save_size);
    if (save_size > 0)
    {
        uint8_t chunk[RAM_CART_CHUNK_SIZE];
        void *fh = SD_FILE_WRITE_OPEN(filename);
        if (fh)
        {
            uint32_t offset = 0;
            while (offset < save_size)
            {
                uint32_t len = save_size - offset;
                if (len > RAM_CART_CHUNK_SIZE)
                    len = RAM_CART_CHUNK_SIZE;
                BUFFER_RAM_BUFFER_READ(offset, chunk, len);
                SD_FILE_WRITE_FILE_CHUNK(fh, chunk, len);
                offset += len;
            }
            SD_FILE_CLOSE(fh);
        }
        DBG_INFO("I write_cart_ram_file(%s) COMPLETE (%lu bytes)\n", filename, save_size);
    }
    else
    {
        DBG_INFO("I write_cart_ram_file(%s) SKIPPED\n", filename);
    }
}