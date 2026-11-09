#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "driver/spi_master.h"

typedef struct psram_qspi_inst
{
    spi_device_handle_t device;
    size_t size;
    bool async_busy;
} psram_qspi_inst_t;

psram_qspi_inst_t psram_qspi_init(void *unused, int sm, float clkdiv);
void psram_qspi_deinit(psram_qspi_inst_t *qspi);
int psram_qspi_test(psram_qspi_inst_t *qspi);
void psram_qspi_write8(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t value);
uint8_t psram_qspi_read8(psram_qspi_inst_t *qspi, uint32_t addr);
void psram_qspi_write16(psram_qspi_inst_t *qspi, uint32_t addr, uint16_t value);
uint16_t psram_qspi_read16(psram_qspi_inst_t *qspi, uint32_t addr);
void psram_qspi_write32(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t value);
uint32_t psram_qspi_read32(psram_qspi_inst_t *qspi, uint32_t addr);
void psram_qspi_write32_async(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t value);
bool psram_qspi_async_is_busy(psram_qspi_inst_t *qspi);
void psram_qspi_async_wait(psram_qspi_inst_t *qspi);
void psram_qspi_write(psram_qspi_inst_t *qspi, uint32_t addr, const uint8_t *src, size_t count);
void psram_qspi_read(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t *dst, size_t count);
void psram_qspi_write_async(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t *src, size_t count);
