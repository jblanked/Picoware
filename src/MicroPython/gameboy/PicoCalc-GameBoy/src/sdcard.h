/**
 * Original source code from https://github.com/carlk3/no-OS-FatFS-SD-SPI-RPi-Pico
 * Copyright 2021 Carl John Kugler III
 *
 * Licensed under the Apache License, Version 2.0 (the License); you may not use
 * this file except in compliance with the License. You may obtain a copy of the
 * License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software distributed
 * under the License is distributed on an AS IS BASIS, WITHOUT WARRANTIES OR
 * CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 *
 */

#pragma once

#include <pico/stdlib.h>
#include <pico/stdio.h>
#include <string.h>
#include "my_debug.h"
#include "f_util.h"
#include "ff.h"
#include "sd_card.h"
#include "diskio.h"

void spi_dma_isr(void);
size_t sd_get_num(void);
sd_card_t *sd_get_by_num(size_t num);
size_t spi_get_num(void);
spi_t *spi_get_by_num(size_t num);

size_t file_read(const char *filename, uint8_t *buffer, size_t buffer_size);
size_t file_size(const char *filename);
bool file_write(const char *filename, const uint8_t *buffer, size_t buffer_size);
size_t file_read_chunk(const char *filename, uint8_t *buffer, size_t buffer_size, size_t offset);
uint16_t file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count);
void *file_open(const char *filename);
void *file_write_open(const char *filename);
void file_close(void *handle);
size_t file_read_file_chunk(void *handle, uint8_t *buffer, size_t buffer_size);
bool file_write_file_chunk(void *handle, const uint8_t *data, size_t size);