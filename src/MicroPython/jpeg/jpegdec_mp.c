// originally from: https://github.com/bjsoftab4/picocalc_viewer/blob/main/jpegdec/jpegdec.c
// JPEGDEC from https://github.com/bitbank2/JPEGDEC
// modified for Picoware by @jblanked
#include "jpegdec_mp.h"

void *JPEGdummy = {readFLASH}; // to avoid compiler error

#if defined(PICOCALC)
#include "../../lcd/lcd_config.h"
#else
#include "../../../lcd/lcd_config.h"
#endif

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

volatile uint8_t core1_running = 0; // 0: stop, 1: run, 2: done
static uint16_t disp_height, disp_width;
static int docode_result;
static JPEGIMAGE _jpeg;
static uint8_t Coremode = 0;

#define CORE1_STACK_SIZE 1024
uint32_t core1_stack[CORE1_STACK_SIZE];

#define FIFO_CMD_DONE (0xffff0ff0)

uint32_t JPEG_msg_core1;

// decode_split runs with multicore
#define FBUFFER_MAX (2)
#define INVALID_MESSAGE (0xffffffff)
volatile struct st_filebuffer
{
    int32_t pos;
    int32_t size; // if size == 0, this buffer is useless
    uint8_t *pbuf;
} JPEG_fbuffer[FBUFFER_MAX];

volatile uint32_t core_message_box;
volatile uint32_t core_message_box2;
volatile uint32_t core_message_box3;

int core1_decode_is_busy();

/* callback funtion from JPEGDEC */
static int JPEGDraw(JPEGDRAW *pDraw)
{
#if defined(LCD_MP_BLIT_16BIT)
    LCD_MP_BLIT_16BIT(pDraw->x, pDraw->y, pDraw->iWidth, pDraw->iHeight, pDraw->pPixels);
#else
    (void)pDraw;
#endif
    return 1;
}

static int JPEGDrawx2(JPEGDRAW *pDraw)
{
    return 1;
}

static void jpeg_param_init(JPEGIMAGE *pJpeg, int iDataSize, uint8_t *pData, JPEG_DRAW_CALLBACK func)
{
#if defined(LCD_MP_WIDTH) && defined(LCD_MP_HEIGHT)
    disp_width = LCD_MP_WIDTH;
    disp_height = LCD_MP_HEIGHT;
#endif
    memset((void *)pJpeg, 0, sizeof(JPEGIMAGE));
    pJpeg->ucMemType = JPEG_MEM_RAM;
    pJpeg->pfnRead = readRAM;
    pJpeg->pfnSeek = seekMem;
    pJpeg->pfnDraw = func;
    pJpeg->pfnOpen = NULL;
    pJpeg->pfnClose = NULL;
    pJpeg->pUser = NULL;
    pJpeg->iError = 1111;
    pJpeg->JPEGFile.iSize = iDataSize;
    pJpeg->JPEGFile.pData = pData;
    pJpeg->ucPixelType = RGB565_LITTLE_ENDIAN;
    pJpeg->iMaxMCUs = 1000; // set to an unnaturally high value to start
}

int core1_decode_is_busy()
{
    uint32_t result;
    if (core1_running == 1)
    {
        return 1;
    }
    result = 0;
    if (multicore_fifo_pop_timeout_us(100, &result))
    {
        JPEG_msg_core1 = result;
    }
    return 0;
}

static int decode_core1_prepare(int drawmode, JPEGIMAGE *pJpeg, int iDataSize, uint8_t *pData, JPEG_DRAW_CALLBACK func)
{
    int result;
    jpeg_param_init(pJpeg, iDataSize, pData, func);
    result = JPEGInit(&_jpeg);
    if (result == 1)
    {
        _jpeg.iOptions = JPEG_USES_DMA;
        JPEG_setCropArea(&_jpeg, 0, 0, disp_width, disp_height);
    }
    return result;
}

void decode_core1_main()
{
    multicore_lockout_victim_init();
    core1_running = 1;
    docode_result = DecodeJPEG(&_jpeg);
    core1_running = 2;
    multicore_fifo_push_timeout_us(FIFO_CMD_DONE, 1000); // wait 1000us
}
void decode_core0_main()
{
    core1_running = 1;
    docode_result = DecodeJPEG(&_jpeg);
    core1_running = 2;
    multicore_fifo_push_timeout_us(FIFO_CMD_DONE, 1000); // wait 1000us
}

static void decode_core1_body(JPEGIMAGE *pJpeg, int core)
{
    while (core1_decode_is_busy())
    {
        tight_loop_contents();
    }
    if (core == 0)
    {
        decode_core0_main();
    }
    else
    {
        multicore_reset_core1();
        multicore_launch_core1_with_stack(decode_core1_main, core1_stack, CORE1_STACK_SIZE);
    }
}

uint32_t get_message_box()
{
    return core_message_box;
}

void set_message_box(uint32_t msg)
{
    core_message_box = msg;
}

uint32_t get_message_box2()
{
    return core_message_box2;
}

void set_message_box2(uint32_t msg)
{
    core_message_box2 = msg;
}

uint32_t get_message_box3()
{
    return core_message_box3;
}

void set_message_box3(uint32_t msg)
{
    core_message_box3 = msg;
}

static void init_fbuffer()
{
    int i;
    for (i = 0; i < FBUFFER_MAX; i++)
    {
        JPEG_fbuffer[i].size = 0;
    }
    set_message_box(INVALID_MESSAGE);
}

static void set_fbuffer(uint32_t bufnum, uint32_t pos, uint8_t *pbuf, uint32_t size)
{
    if (bufnum < FBUFFER_MAX)
    {
        JPEG_fbuffer[bufnum].pos = pos;
        JPEG_fbuffer[bufnum].pbuf = pbuf;
        JPEG_fbuffer[bufnum].size = size; // set size at last
    }
}

static int testAndSetBuffer(int32_t *p_iPos, int32_t *p_iLen, uint8_t **p_dstBuf)
{
    int i;
    int retc = -1;
    int32_t bufPos, bufLen;
    int32_t iPos = *p_iPos, iLen = *p_iLen;
    uint8_t *dstBuf = *p_dstBuf;

    for (i = 0; i < FBUFFER_MAX; i++)
    {
        if (JPEG_fbuffer[i].size == 0)
        {
            continue;
        }
        bufPos = JPEG_fbuffer[i].pos;
        bufLen = JPEG_fbuffer[i].size;
        if (bufPos <= iPos)
        {
            if (iPos + iLen <= bufPos + bufLen)
            {
                memcpy(dstBuf, JPEG_fbuffer[i].pbuf + (iPos - bufPos), iLen);
                *p_dstBuf += iLen;
                iPos += iLen;
                iLen = 0;
                *p_iPos = iPos;
                *p_iLen = iLen;
                retc = i; // normal end
                return retc;
            }
            if (iPos < bufPos + bufLen)
            { // found 1st part
                int32_t size_1st = bufPos + bufLen - iPos;
                memcpy(dstBuf, JPEG_fbuffer[i].pbuf + (iPos - bufPos), size_1st);
                dstBuf += size_1st;
                iPos += size_1st;
                iLen -= size_1st;
                JPEG_fbuffer[i].size = 0; // buffer i is empty
                *p_dstBuf = dstBuf;
                *p_iPos = iPos; // set new iPos, iLen
                *p_iLen = iLen;
                retc = 0x200 | i; // i is empty and need reading
                return retc;
            }
        }
    }
    return retc;
}

static int32_t readRAM_split(JPEGFILE *pFile, uint8_t *pBuf, int32_t iLen)
{
    int rc;
    int iBytesRead;
    int32_t iPos = pFile->iPos;
    int32_t iLen_sav = iLen;

    do
    {
        rc = testAndSetBuffer(&iPos, &iLen, &pBuf);
        if (rc < 0)
        {
            set_message_box3(-1);
            set_message_box2(iLen);
            set_message_box(iPos);
            sleep_ms(0);
            continue;
        }
        if ((rc & 0x200) != 0)
        { // copied only 1st part
            set_message_box3(rc);
            set_message_box2(iLen); // request new buffer
            set_message_box(iPos);
            sleep_ms(0);
            rc = -1;
            continue;
        }
    } while (rc < 0);

    // return used buffer, or inform buffer empty
    set_message_box3(rc);
    set_message_box2(0); // inform next iPos
    set_message_box(iPos);
    iBytesRead = iLen_sav;
    pFile->iPos += iLen_sav;
    return iBytesRead;
}

static int32_t seekMem_split(JPEGFILE *pFile, int32_t iPosition)
{
    if (iPosition < 0)
    {
        iPosition = 0;
    }
    else if (iPosition >= pFile->iSize)
    {
        iPosition = pFile->iSize - 1;
    }
    pFile->iPos = iPosition;
    return iPosition;
}

static void jpeg_param_init_split(JPEGIMAGE *pJpeg, int iDataSize, uint8_t *pData, JPEG_DRAW_CALLBACK func)
{
    jpeg_param_init(pJpeg, iDataSize, pData, func);
    pJpeg->pfnRead = readRAM_split;
    pJpeg->pfnSeek = seekMem_split;
}

static void decode_core1_split()
{
    multicore_lockout_victim_init();
    core1_running = 1;
    docode_result = DecodeJPEG(&_jpeg);
    core1_running = 2;
}

//--- mp functions

const mp_obj_type_t jpegdec_mp_type;

void jpegdec_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "JPEGDecoder(initialized=");
    mp_print_str(print, self->initialized ? "True" : "False");
    mp_print_str(print, ")");
}

mp_obj_t jpegdec_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    jpegdec_mp_obj_t *self = mp_obj_malloc_with_finaliser(jpegdec_mp_obj_t, &jpegdec_mp_type);
    self->base.type = &jpegdec_mp_type;
    self->context = &_jpeg;
    self->initialized = true;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t jpegdec_mp_del(mp_obj_t self_in)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->context = NULL;
    self->initialized = false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(jpegdec_mp_del_obj, jpegdec_mp_del);

void jpegdec_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] != MP_OBJ_NULL)
    {
        if (attribute == MP_QSTR_initialized)
        {
            destination[0] = mp_obj_new_bool(self->initialized);
        }
        else if (attribute == MP_QSTR_context)
        {
            // this obvs wont work lol I'll come back to this
            destination[0] = MP_OBJ_FROM_PTR(self->context);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&jpegdec_mp_del_obj);
        }
    }
}
mp_obj_t jpegdec_decode(mp_obj_t self_in, mp_obj_t data)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(data, &inbuf, MP_BUFFER_READ);

    if (self->initialized && decode_core1_prepare(0, &_jpeg, inbuf.len, (uint8_t *)inbuf.buf, JPEGDraw) == 1)
    {
        if (DecodeJPEG(&_jpeg) == 1)
        {
            mp_obj_t res[3] = {
                mp_const_true,
                mp_obj_new_int(_jpeg.iWidth),
                mp_obj_new_int(_jpeg.iHeight)};

            return mp_obj_new_tuple(3, res);
        }
    }

    mp_obj_t res[3] = {
        mp_const_false,
        mp_obj_new_int(0),
        mp_obj_new_int(0)};

    return mp_obj_new_tuple(3, res);
}
static MP_DEFINE_CONST_FUN_OBJ_2(jpegdec_decode_obj, jpegdec_decode);

mp_obj_t jpegdec_decodex2(size_t n_args, const mp_obj_t *args)
{
    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(args[1], &inbuf, MP_BUFFER_READ);
    jpeg_param_init(&_jpeg, inbuf.len, (uint8_t *)inbuf.buf, JPEGDrawx2);

    if (JPEGInit(&_jpeg) == 1)
    {
        _jpeg.iOptions = JPEG_USES_DMA;
        JPEG_setCropArea(&_jpeg, 0, 0, disp_width / 2, disp_height / 2);
        if (DecodeJPEG(&_jpeg) == 1)
        {
            mp_obj_t res[3] = {
                mp_const_true,
                mp_obj_new_int(_jpeg.iWidth),
                mp_obj_new_int(_jpeg.iHeight)};

            return mp_obj_new_tuple(3, res);
        }
    }

    mp_obj_t res[3] = {
        mp_const_false,
        mp_obj_new_int(0),
        mp_obj_new_int(0)};

    return mp_obj_new_tuple(3, res);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decodex2_obj, 2, 2, jpegdec_decodex2);

mp_obj_t jpegdec_decode_core(size_t n_args, const mp_obj_t *args)
{
    // args: self, buffer, run_core (0 or 1), optional tuple with x and y offset
    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(args[1], &inbuf, MP_BUFFER_READ);
    int result = 0;
    int drawmode = 0;
    int run_core = 0;
    if (n_args >= 3)
    {
        run_core = mp_obj_get_int(args[2]); // mode 0:single core, 1:core1
    }
    int ofst_x = 0, ofst_y = 0;
    mp_obj_t *tuple_data = NULL;
    size_t tuple_len = 0;
    if (n_args >= 4)
    {
        if (args[3] != mp_const_none)
        {
            mp_obj_tuple_get(args[3], &tuple_len, &tuple_data);
            if (tuple_len >= 2)
            {
                ofst_x = mp_obj_get_int(tuple_data[0]);
                ofst_y = mp_obj_get_int(tuple_data[1]);
            }
        }
    }
    Coremode = (uint8_t)(run_core);
    while (core1_decode_is_busy())
    {
        tight_loop_contents();
    }
    if (core1_running == 2)
    {
        result = docode_result;
        core1_running = 0;
    }

    if (decode_core1_prepare(drawmode, &_jpeg, inbuf.len, (uint8_t *)inbuf.buf, JPEGDraw) == 1)
    {
        _jpeg.iXOffset = ofst_x;
        _jpeg.iYOffset = ofst_y;
        decode_core1_body(&_jpeg, run_core);
        result = 1;
    }

    mp_obj_t res[4] = {
        mp_obj_new_bool(result == 1),
        mp_obj_new_int(_jpeg.iWidth),
        mp_obj_new_int(_jpeg.iHeight)};

    return mp_obj_new_tuple(3, res);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decode_core_obj, 2, 4, jpegdec_decode_core);

mp_obj_t jpegdec_decode_core_stat(mp_obj_t self_in)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->initialized ? (int)core1_running : -1);
}
static MP_DEFINE_CONST_FUN_OBJ_1(jpegdec_decode_core_stat_obj, jpegdec_decode_core_stat);

mp_obj_t jpegdec_decode_core_wait(size_t n_args, const mp_obj_t *args)
{
    int result = 1;
    int res1 = 0;
    int res2 = 0;
    int timeout;
    if (n_args == 2)
    { // force stop
        timeout = mp_obj_get_int(args[1]);
    }
    else
    {
        timeout = 1000;
    }
    for (; timeout >= 0; timeout--)
    {
        if (core1_decode_is_busy() == 0)
        {
            break;
        }
        sleep_ms(1);
    }
    if (timeout < 0)
    {
        if (Coremode == 1)
        {
            multicore_reset_core1();
            core1_running = 0;
            result = 0;
        }
    }
    if (core1_running == 2)
    {
        result = docode_result;
        core1_running = 0;
    }
    int res3 = (int)core1_running;
    mp_obj_t res[4] = {
        mp_obj_new_bool(result == 1),
        mp_obj_new_int(res1),
        mp_obj_new_int(res2),
        mp_obj_new_int(res3),
    };

    return mp_obj_new_tuple(4, res);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decode_core_wait_obj, 1, 2, jpegdec_decode_core_wait);

// decode_opt runs with multicore
mp_obj_t jpegdec_decode_opt(size_t n_args, const mp_obj_t *args)
{
    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(args[1], &inbuf, MP_BUFFER_READ);

    int ofst_x = 0, ofst_y = 0, clip_x = 0, clip_y = 0, clip_w = disp_width, clip_h = disp_height;
    int ioption = 0;
    // get tuple
    mp_obj_t *tuple_data = NULL;
    size_t tuple_len = 0;
    if (n_args >= 3)
    {
        mp_obj_tuple_get(args[2], &tuple_len, &tuple_data);
        if (tuple_len >= 2)
        {
            ofst_x = mp_obj_get_int(tuple_data[0]);
            ofst_y = mp_obj_get_int(tuple_data[1]);
        }
    }
    if (n_args >= 4)
    {
        mp_obj_tuple_get(args[3], &tuple_len, &tuple_data);
        if (tuple_len >= 4)
        {
            clip_x = mp_obj_get_int(tuple_data[0]);
            clip_y = mp_obj_get_int(tuple_data[1]);
            clip_w = mp_obj_get_int(tuple_data[2]);
            clip_h = mp_obj_get_int(tuple_data[3]);
        }
    }
    if (n_args >= 5)
    {
        ioption = mp_obj_get_int(args[4]);
    }

    jpeg_param_init(&_jpeg, inbuf.len, (uint8_t *)inbuf.buf, JPEGDraw);
    if (JPEGInit(&_jpeg) == 1)
    {
        _jpeg.iXOffset = ofst_x;
        _jpeg.iYOffset = ofst_y;
        _jpeg.iOptions = ioption | JPEG_USES_DMA;
        JPEG_setCropArea(&_jpeg, clip_x, clip_y, clip_w, clip_h);
        if (DecodeJPEG(&_jpeg) == 1)
        {
            mp_obj_t res[4] = {
                mp_const_true,
                mp_obj_new_int(_jpeg.iWidth),
                mp_obj_new_int(_jpeg.iHeight)};

            return mp_obj_new_tuple(3, res);
        }
    }

    mp_obj_t res[3] = {
        mp_const_false,
        mp_obj_new_int(0),
        mp_obj_new_int(0)};

    return mp_obj_new_tuple(3, res);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decode_opt_obj, 2, 5, jpegdec_decode_opt);

mp_obj_t jpegdec_decode_split(size_t n_args, const mp_obj_t *args)
{
    // args[0] self, args[1] filesize, args[2] buf, [ args[3] ofset, args[4] clip, args[5] option ]
    int result = 0;
    int result0 = -1;

    mp_obj_t *tuple_data = NULL;
    size_t tuple_len = 0;

    while (core1_decode_is_busy())
    {
        tight_loop_contents();
    }
    if (core1_running == 2)
    {
        result0 = docode_result;
        core1_running = 0;
    }

    init_fbuffer();
    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(args[2], &inbuf, MP_BUFFER_READ);
    set_fbuffer(0, 0, (uint8_t *)inbuf.buf, inbuf.len);

    bool f_clip = false;
    int ofst_x = 0, ofst_y = 0, clip_x, clip_y, clip_w, clip_h;
    int ioption = 0;
    // get tuple
    if (n_args >= 4)
    {
        if (args[3] != mp_const_none)
        {
            mp_obj_tuple_get(args[3], &tuple_len, &tuple_data);
            if (tuple_len >= 2)
            {
                ofst_x = mp_obj_get_int(tuple_data[0]);
                ofst_y = mp_obj_get_int(tuple_data[1]);
            }
        }
    }
    if (n_args >= 5)
    {
        if (args[4] != mp_const_none)
        {
            mp_obj_tuple_get(args[4], &tuple_len, &tuple_data);
            if (tuple_len >= 4)
            {
                f_clip = true;
                clip_x = mp_obj_get_int(tuple_data[0]);
                clip_y = mp_obj_get_int(tuple_data[1]);
                clip_w = mp_obj_get_int(tuple_data[2]);
                clip_h = mp_obj_get_int(tuple_data[3]);
            }
        }
    }
    if (n_args >= 6)
    {
        ioption = mp_obj_get_int(args[5]);
    }

    jpeg_param_init_split(&_jpeg, mp_obj_get_int(args[1]), inbuf.buf, JPEGDraw);
    result = JPEGInit(&_jpeg);
    if (result == 1)
    {
        _jpeg.iXOffset = ofst_x;
        _jpeg.iYOffset = ofst_y;
        _jpeg.iOptions = ioption | JPEG_USES_DMA;
        if (f_clip)
        {
            JPEG_setCropArea(&_jpeg, clip_x, clip_y, clip_w, clip_h);
        }

        multicore_reset_core1();
        multicore_launch_core1_with_stack(decode_core1_split, core1_stack, CORE1_STACK_SIZE);
    }

    mp_obj_t res[4] = {
        mp_obj_new_bool(result == 1),
        mp_obj_new_int(_jpeg.iWidth),
        mp_obj_new_int(_jpeg.iHeight),
        mp_obj_new_bool(result0 == 1)};

    return mp_obj_new_tuple(4, res);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decode_split_obj, 3, 6, jpegdec_decode_split);

mp_obj_t jpegdec_decode_split_buffer(size_t n_args, const mp_obj_t *args)
{
    // self, buffer num, filepointer, buffer
    const int bufnum = mp_obj_get_int(args[1]);

    if (bufnum >= FBUFFER_MAX)
    {
        PRINT("Invalid buffer number: %d\n", bufnum);
        return mp_const_false;
    }

    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(args[3], &inbuf, MP_BUFFER_READ);
    set_fbuffer(bufnum, mp_obj_get_int(args[2]), (uint8_t *)inbuf.buf, inbuf.len);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(jpegdec_decode_split_buffer_obj, 4, 4, jpegdec_decode_split_buffer);

mp_obj_t jpegdec_decode_split_wait(mp_obj_t self_in)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_obj_t res[4] = {
            mp_obj_new_int(-1),
            mp_obj_new_int(0),
            mp_obj_new_int(0),
            mp_obj_new_int(0),
        };
        return mp_obj_new_tuple(4, res);
    }
    int result = 0;
    int res1 = INVALID_MESSAGE;
    int res2 = 0;
    int res3 = 0;
    if (core1_running == 1)
    { // core1 is running
        res1 = get_message_box();
        res2 = get_message_box2();
        res3 = get_message_box3();
        if (res1 != INVALID_MESSAGE)
        {
            set_message_box(INVALID_MESSAGE);
        }
    }
    else if (core1_running == 2)
    {                               // core1 done
        res2 = (int)JPEG_msg_core1; // core1 result
        res1 = docode_result;
        core1_running = 0;
        result = 1;
    }
    else
    { // core1 does nothing
        result = 1;
    }
    mp_obj_t res[4] = {
        mp_obj_new_int(result), // 0: running, 1: done
        mp_obj_new_int(res1),   // if result==0 : message_box(required filepointer)
                                // if result==1 : core1 decode result
        mp_obj_new_int(res2),   // if result==0 : message_box(required datasize)
        mp_obj_new_int(res3),   // if result==0 : message_box(index information)
    };

    return mp_obj_new_tuple(4, res);
}
static MP_DEFINE_CONST_FUN_OBJ_1(jpegdec_decode_split_wait_obj, jpegdec_decode_split_wait);

mp_obj_t jpegdec_getinfo(mp_obj_t self_in, mp_obj_t data)
{
    jpegdec_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int result = self->initialized ? 1 : 0;

    mp_buffer_info_t inbuf;
    mp_get_buffer_raise(data, &inbuf, MP_BUFFER_READ);
    int iDataSize = inbuf.len;
    uint8_t *pData = (uint8_t *)inbuf.buf;
    while (core1_decode_is_busy())
    {
        tight_loop_contents();
    }

    jpeg_param_init(&_jpeg, iDataSize, pData, JPEGDraw);
    result = JPEGInit(&_jpeg);
    mp_obj_t res[6] = {
        mp_obj_new_bool(result == 1),
        mp_obj_new_int(_jpeg.iWidth),
        mp_obj_new_int(_jpeg.iHeight),
        mp_obj_new_int((int)(&_jpeg)),
        mp_obj_new_int(0),
        mp_obj_new_int(0),
    };
    return mp_obj_new_tuple(6, res);
}
static MP_DEFINE_CONST_FUN_OBJ_2(jpegdec_getinfo_obj, jpegdec_getinfo);

static const mp_rom_map_elem_t jpegdec_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_decode), MP_ROM_PTR(&jpegdec_decode_obj)},
    {MP_ROM_QSTR(MP_QSTR_decodex2), MP_ROM_PTR(&jpegdec_decodex2_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_core), MP_ROM_PTR(&jpegdec_decode_core_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_core_stat), MP_ROM_PTR(&jpegdec_decode_core_stat_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_core_wait), MP_ROM_PTR(&jpegdec_decode_core_wait_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_opt), MP_ROM_PTR(&jpegdec_decode_opt_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_split), MP_ROM_PTR(&jpegdec_decode_split_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_split_wait), MP_ROM_PTR(&jpegdec_decode_split_wait_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode_split_buffer), MP_ROM_PTR(&jpegdec_decode_split_buffer_obj)},
    {MP_ROM_QSTR(MP_QSTR_getinfo), MP_ROM_PTR(&jpegdec_getinfo_obj)},
};
static MP_DEFINE_CONST_DICT(jpegdec_locals_dict, jpegdec_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    jpegdec_mp_type,
    MP_QSTR_JPEGDecoder,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, jpegdec_mp_print,
    make_new, jpegdec_mp_make_new,
    attr, jpegdec_mp_attr,
    locals_dict, &jpegdec_locals_dict);

static const mp_rom_map_elem_t jpegdec_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_jpegdec)},
    {MP_ROM_QSTR(MP_QSTR_JPEGDecoder), MP_ROM_PTR(&jpegdec_mp_type)},
};
static MP_DEFINE_CONST_DICT(jpegdec_globals, jpegdec_globals_table);

const mp_obj_module_t jpegdec_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&jpegdec_globals,
};

MP_REGISTER_MODULE(MP_QSTR_jpegdec, jpegdec_cmodule);
