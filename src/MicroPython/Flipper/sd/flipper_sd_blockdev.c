#include "flipper_sd_blockdev.h"
#include "py/runtime.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/mperrno.h"
#include "extmod/vfs.h"
#include <string.h>

// VFS block protocol: readblocks
static mp_obj_t blockdev_readblocks(size_t n_args, const mp_obj_t *args)
{
    flipper_sd_blockdev_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t block_num = mp_obj_get_int(args[1]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[2], &bufinfo, MP_BUFFER_WRITE);

    mp_int_t offset = 0;
    if (n_args >= 4)
    {
        offset = mp_obj_get_int(args[3]);
    }

    if (offset != 0)
    {
        // Read full block into stack buf, copy out partial
        uint8_t tmp[512];
        if (spi_sdcard_read_blocks(self->card, tmp, (uint32_t)block_num, 1) != 0)
            mp_raise_OSError(MP_EIO);
        size_t copy_len = bufinfo.len;
        if (offset + copy_len > 512)
            copy_len = 512 - offset;
        memcpy(bufinfo.buf, tmp + offset, copy_len);
    }
    else
    {
        uint32_t num_blocks = (uint32_t)(bufinfo.len / self->block_size);
        if (num_blocks == 0)
            num_blocks = 1;
        if (spi_sdcard_read_blocks(self->card, bufinfo.buf,
                                   (uint32_t)block_num, num_blocks) != 0)
            mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(blockdev_readblocks_obj, 3, 4,
                                           blockdev_readblocks);

// VFS block protocol: writeblocks
static mp_obj_t blockdev_writeblocks(size_t n_args, const mp_obj_t *args)
{
    flipper_sd_blockdev_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t block_num = mp_obj_get_int(args[1]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[2], &bufinfo, MP_BUFFER_READ);

    mp_int_t offset = 0;
    if (n_args >= 4)
    {
        offset = mp_obj_get_int(args[3]);
    }

    if (offset != 0)
    {
        // Read-modify-write for partial block
        uint8_t tmp[512];
        if (spi_sdcard_read_blocks(self->card, tmp, (uint32_t)block_num, 1) != 0)
            mp_raise_OSError(MP_EIO);
        memcpy(tmp + offset, bufinfo.buf, bufinfo.len);
        if (spi_sdcard_write_blocks(self->card, tmp, (uint32_t)block_num, 1) != 0)
            mp_raise_OSError(MP_EIO);
    }
    else
    {
        uint32_t num_blocks = (uint32_t)(bufinfo.len / self->block_size);
        if (num_blocks == 0)
            num_blocks = 1;
        if (spi_sdcard_write_blocks(self->card, bufinfo.buf,
                                    (uint32_t)block_num, num_blocks) != 0)
            mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(blockdev_writeblocks_obj, 3, 4,
                                           blockdev_writeblocks);

// VFS block protocol: ioctl
static mp_obj_t blockdev_ioctl(mp_obj_t self_in, mp_obj_t op_in,
                               mp_obj_t arg_in)
{
    flipper_sd_blockdev_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t op = mp_obj_get_int(op_in);

    switch (op)
    {
    case MP_BLOCKDEV_IOCTL_INIT:
        return mp_const_none;

    case MP_BLOCKDEV_IOCTL_DEINIT:
        spi_sdcard_deinit(self->card);
        return mp_const_none;

    case MP_BLOCKDEV_IOCTL_SYNC:
        return mp_const_none;

    case MP_BLOCKDEV_IOCTL_BLOCK_COUNT:
        return mp_obj_new_int_from_uint(self->block_count);

    case MP_BLOCKDEV_IOCTL_BLOCK_SIZE:
        return mp_obj_new_int_from_uint(self->block_size);

    default:
        mp_raise_ValueError(MP_ERROR_TEXT("unsupported ioctl"));
    }
}
static MP_DEFINE_CONST_FUN_OBJ_3(blockdev_ioctl_obj, blockdev_ioctl);

// Constructor - card is attached later via flipper_sd_blockdev_set_card

static mp_obj_t blockdev_make_new(const mp_obj_type_t *type, size_t n_args,
                                  size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    flipper_sd_blockdev_obj_t *self =
        mp_obj_malloc(flipper_sd_blockdev_obj_t, type);
    self->card = NULL;
    self->block_count = 0;
    self->block_size = 512;
    return MP_OBJ_FROM_PTR(self);
}

void flipper_sd_blockdev_set_card(mp_obj_t blockdev_obj, spi_sdcard_t *card,
                                  uint32_t block_count, uint32_t block_size)
{
    flipper_sd_blockdev_obj_t *self = MP_OBJ_TO_PTR(blockdev_obj);
    self->card = card;
    self->block_count = block_count;
    self->block_size = block_size;
}

static const mp_rom_map_elem_t blockdev_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_readblocks), MP_ROM_PTR(&blockdev_readblocks_obj)},
    {MP_ROM_QSTR(MP_QSTR_writeblocks), MP_ROM_PTR(&blockdev_writeblocks_obj)},
    {MP_ROM_QSTR(MP_QSTR_ioctl), MP_ROM_PTR(&blockdev_ioctl_obj)},
};
static MP_DEFINE_CONST_DICT(blockdev_locals_dict, blockdev_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    flipper_sd_blockdev_type,
    MP_QSTR_FlipperSDBlockDev,
    MP_TYPE_FLAG_NONE,
    make_new, blockdev_make_new,
    locals_dict, &blockdev_locals_dict);
