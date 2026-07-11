#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../src/MicroPython/JPEGDEC/src/JPEGDEC.h"

struct Bitmap {
    int width;
    int height;
    uint16_t *pixels;
};

static int draw_block(JPEGDRAW *draw) {
    Bitmap *bmp = (Bitmap *)draw->pUser;
    if (bmp == NULL || bmp->pixels == NULL || draw->pPixels == NULL) {
        return 0;
    }
    for (int yy = 0; yy < draw->iHeight; yy++) {
        int dst_y = draw->y + yy;
        if (dst_y < 0 || dst_y >= bmp->height) {
            continue;
        }
        for (int xx = 0; xx < draw->iWidth; xx++) {
            int dst_x = draw->x + xx;
            if (dst_x < 0 || dst_x >= bmp->width) {
                continue;
            }
            bmp->pixels[dst_y * bmp->width + dst_x] =
                draw->pPixels[yy * draw->iWidth + xx];
        }
    }
    return 1;
}

static uint8_t *read_file(const char *path, size_t *out_size) {
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        return NULL;
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    long size = ftell(file);
    if (size <= 0) {
        fclose(file);
        return NULL;
    }
    rewind(file);
    uint8_t *data = (uint8_t *)malloc((size_t)size);
    if (data == NULL) {
        fclose(file);
        return NULL;
    }
    if (fread(data, 1, (size_t)size, file) != (size_t)size) {
        free(data);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *out_size = (size_t)size;
    return data;
}

static void put_u16(uint8_t *buf, int off, uint16_t value) {
    buf[off] = (uint8_t)(value & 0xff);
    buf[off + 1] = (uint8_t)((value >> 8) & 0xff);
}

static void put_u32(uint8_t *buf, int off, uint32_t value) {
    buf[off] = (uint8_t)(value & 0xff);
    buf[off + 1] = (uint8_t)((value >> 8) & 0xff);
    buf[off + 2] = (uint8_t)((value >> 16) & 0xff);
    buf[off + 3] = (uint8_t)((value >> 24) & 0xff);
}

static int write_bmp_rgb565(const char *path, const Bitmap *bmp) {
    FILE *file = fopen(path, "wb");
    if (file == NULL) {
        return 0;
    }
    int row_bytes = ((bmp->width * 16 + 31) / 32) * 4;
    int image_bytes = row_bytes * bmp->height;
    int header_bytes = 14 + 40 + 12;
    int file_bytes = header_bytes + image_bytes;
    uint8_t header[66];
    memset(header, 0, sizeof(header));
    header[0] = 'B';
    header[1] = 'M';
    put_u32(header, 2, (uint32_t)file_bytes);
    put_u32(header, 10, (uint32_t)header_bytes);
    put_u32(header, 14, 40);
    put_u32(header, 18, (uint32_t)bmp->width);
    put_u32(header, 22, (uint32_t)(-bmp->height));
    put_u16(header, 26, 1);
    put_u16(header, 28, 16);
    put_u32(header, 30, 3);
    put_u32(header, 34, (uint32_t)image_bytes);
    put_u32(header, 54, 0x0000f800);
    put_u32(header, 58, 0x000007e0);
    put_u32(header, 62, 0x0000001f);
    if (fwrite(header, 1, sizeof(header), file) != sizeof(header)) {
        fclose(file);
        return 0;
    }
    uint8_t *row = (uint8_t *)calloc((size_t)row_bytes, 1);
    if (row == NULL) {
        fclose(file);
        return 0;
    }
    for (int y = 0; y < bmp->height; y++) {
        memset(row, 0, (size_t)row_bytes);
        for (int x = 0; x < bmp->width; x++) {
            uint16_t pixel = bmp->pixels[y * bmp->width + x];
            row[x * 2] = (uint8_t)(pixel & 0xff);
            row[x * 2 + 1] = (uint8_t)((pixel >> 8) & 0xff);
        }
        if (fwrite(row, 1, (size_t)row_bytes, file) != (size_t)row_bytes) {
            free(row);
            fclose(file);
            return 0;
        }
    }
    free(row);
    fclose(file);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s input.jpg output.bmp [scale]\n", argv[0]);
        return 2;
    }
    int option = 0;
    if (argc >= 4) {
        int scale = atoi(argv[3]);
        if (scale == 2 || scale == 4 || scale == 8) {
            option = scale;
        }
    }
    size_t data_size = 0;
    uint8_t *data = read_file(argv[1], &data_size);
    if (data == NULL) {
        fprintf(stderr, "failed to read %s\n", argv[1]);
        return 3;
    }
    JPEGDEC jpeg;
    if (!jpeg.openRAM(data, (int)data_size, draw_block)) {
        fprintf(stderr, "JPEGDEC openRAM failed\n");
        free(data);
        return 4;
    }
    int width = jpeg.getWidth();
    int height = jpeg.getHeight();
    int divisor = option ? option : 1;
    Bitmap bmp;
    bmp.width = (width + divisor - 1) / divisor;
    bmp.height = (height + divisor - 1) / divisor;
    bmp.pixels = (uint16_t *)calloc((size_t)bmp.width * (size_t)bmp.height, 2);
    if (bmp.pixels == NULL) {
        free(data);
        return 5;
    }
    jpeg.setUserPointer(&bmp);
    jpeg.setPixelType(RGB565_LITTLE_ENDIAN);
    int ok = jpeg.decode(0, 0, option ? option : 0);
    jpeg.close();
    if (!ok || !write_bmp_rgb565(argv[2], &bmp)) {
        free(bmp.pixels);
        free(data);
        return 6;
    }
    free(bmp.pixels);
    free(data);
    return 0;
}
