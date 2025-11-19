/*
 * @Author: flyingtjy flyingtjy@gmail.com
 * @Date: 2025-04-15 10:08:01
 * @LastEditors: flyingtjy flyingtjy@gmail.com
 * @LastEditTime: 2025-04-15 11:25:18
 * @FilePath: \dispaly_test\libraries\pio_drive\pio_qspi.h
 * @Description:
 *
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved.
 */
#ifndef __PIO_QSPI_H__
#define __PIO_QSPI_H__
#include "pico/stdlib.h"
#include <stdio.h>
#include "bsp_dma_channel_irq.h"

#define QSPI_PIO pio2

void pio_qspi_init(uint sclk_pin, uint d0_pin, uint32_t baudrate, channel_irq_callback_t irq_cb);

void pio_qspi_1bit_write_blocking(uint8_t buf);

void pio_qspi_1bit_write_data_blocking(uint8_t *buf, size_t len);
void pio_qspi_4bit_write_data_blocking(uint8_t *buf, size_t len);

void pio_qspi_1bit_write_data(uint8_t *buf, size_t len);
void pio_qspi_4bit_write_data(uint8_t *buf, size_t len);

int pio_qspi_get_dma_channel(void);
uint pio_qspi_get_sm(void);

#endif