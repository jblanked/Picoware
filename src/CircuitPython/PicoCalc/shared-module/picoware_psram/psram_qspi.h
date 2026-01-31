/******************************************************************************
 * picoware-psram QSPI Interface Header
 *
 * Enhanced QSPI driver for PSRAM inspired by Waveshare implementation
 * Provides high-speed 4-wire transfers with DMA support
 *
 * Copyright © 2023 Ian Scott (original SPI implementation)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 ******************************************************************************/

#pragma once

#ifndef _PSRAM_QSPI_H_
#define _PSRAM_QSPI_H_

// Configuration defines
#define PSRAM_QSPI_PIN_CS 20
#define PSRAM_QSPI_PIN_SCK 21 // Must be CS + 1 for sideset
#define PSRAM_QSPI_PIN_SIO0 2 // SIO0-3 must be consecutive (2, 3, 4, 5)

// Feature flags
#define PSRAM_QSPI_USE_DMA 1
#define PSRAM_QSPI_SPINLOCK 1
#define PSRAM_QSPI_ASYNC 1

#include "hardware/pio.h"
#include "hardware/gpio.h"
#include "hardware/dma.h"
#include "hardware/timer.h"
#include "hardware/sync.h"
#include "psram_qspi.pio.h"
#include <string.h>

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * @brief QSPI PSRAM instance configuration
     */
    typedef struct psram_qspi_inst
    {
        PIO pio;
        int sm;
        uint offset;
        float clkdiv;

        // Pin configuration
        uint8_t pin_cs;
        uint8_t pin_sck;
        uint8_t pin_sio0; // Base pin for SIO0-3

        // Synchronization
#if defined(PSRAM_QSPI_SPINLOCK)
        spin_lock_t *spinlock;
        uint32_t spin_irq_state;
#endif

        // DMA channels
#if defined(PSRAM_QSPI_USE_DMA)
        int write_dma_chan;
        dma_channel_config write_dma_cfg;
        int read_dma_chan;
        dma_channel_config read_dma_cfg;
#endif

#if defined(PSRAM_QSPI_ASYNC)
        int async_dma_chan;
        dma_channel_config async_dma_cfg;
        volatile bool async_busy;
#endif
    } psram_qspi_inst_t;

// Global async instance pointer
#if defined(PSRAM_QSPI_ASYNC)
    extern psram_qspi_inst_t *qspi_async_inst;
#endif

    /**
     * @brief Initialize PSRAM QSPI interface
     *
     * @param pio PIO instance (pio0 or pio1)
     * @param sm State machine number (-1 for auto)
     * @param clkdiv Clock divider (1.0 for full speed, 2.0 for stability)
     * @return Initialized QSPI instance
     */
    psram_qspi_inst_t psram_qspi_init(PIO pio, int sm, float clkdiv);

    /**
     * @brief Deinitialize PSRAM QSPI interface
     */
    void psram_qspi_deinit(psram_qspi_inst_t *qspi);

    /**
     * @brief Test PSRAM functionality
     */
    int psram_qspi_test(psram_qspi_inst_t *qspi);

// =============================================================================
// Lock/Unlock macros for thread safety
// =============================================================================
#if defined(PSRAM_QSPI_SPINLOCK)
#define PSRAM_QSPI_LOCK(qspi) \
    (qspi)->spin_irq_state = spin_lock_blocking((qspi)->spinlock)
#define PSRAM_QSPI_UNLOCK(qspi) \
    spin_unlock((qspi)->spinlock, (qspi)->spin_irq_state)
#else
#define PSRAM_QSPI_LOCK(qspi)
#define PSRAM_QSPI_UNLOCK(qspi)
#endif

    // =============================================================================
    // Low-level PIO write/read functions
    // =============================================================================

    /**
     * @brief Write data to PIO TX FIFO using DMA (blocking)
     */
    __force_inline static void __time_critical_func(qspi_write_dma_blocking)(
        psram_qspi_inst_t *qspi,
        const uint8_t *src, size_t len)
    {
        PSRAM_QSPI_LOCK(qspi);

#if defined(PSRAM_QSPI_USE_DMA)
        dma_channel_transfer_from_buffer_now(qspi->write_dma_chan, src, len);
        dma_channel_wait_for_finish_blocking(qspi->write_dma_chan);
#else
    io_rw_8 *txfifo = (io_rw_8 *)&qspi->pio->txf[qspi->sm];
    for (size_t i = 0; i < len; i++)
    {
        while (pio_sm_is_tx_fifo_full(qspi->pio, qspi->sm))
            tight_loop_contents();
        *txfifo = src[i];
    }
#endif

        PSRAM_QSPI_UNLOCK(qspi);
    }

    /**
     * @brief Write and read data using DMA (blocking)
     */
    __force_inline static void __time_critical_func(qspi_write_read_dma_blocking)(
        psram_qspi_inst_t *qspi,
        const uint8_t *src, size_t src_len,
        uint8_t *dst, size_t dst_len)
    {
        PSRAM_QSPI_LOCK(qspi);

#if defined(PSRAM_QSPI_USE_DMA)
        dma_channel_transfer_from_buffer_now(qspi->write_dma_chan, src, src_len);
        if (dst_len > 0)
        {
            dma_channel_transfer_to_buffer_now(qspi->read_dma_chan, dst, dst_len);
        }
        dma_channel_wait_for_finish_blocking(qspi->write_dma_chan);
        if (dst_len > 0)
        {
            dma_channel_wait_for_finish_blocking(qspi->read_dma_chan);
        }
#else
    // CPU-driven fallback
    io_rw_8 *txfifo = (io_rw_8 *)&qspi->pio->txf[qspi->sm];
    io_rw_8 *rxfifo = (io_rw_8 *)&qspi->pio->rxf[qspi->sm];

    for (size_t i = 0; i < src_len; i++)
    {
        while (pio_sm_is_tx_fifo_full(qspi->pio, qspi->sm))
            tight_loop_contents();
        *txfifo = src[i];
    }

    for (size_t i = 0; i < dst_len; i++)
    {
        while (pio_sm_is_rx_fifo_empty(qspi->pio, qspi->sm))
            tight_loop_contents();
        dst[i] = *rxfifo;
    }
#endif

        PSRAM_QSPI_UNLOCK(qspi);
    }

/**
 * @brief Async write using DMA (non-blocking)
 */
#if defined(PSRAM_QSPI_ASYNC)
    __force_inline static void __time_critical_func(qspi_write_async)(
        psram_qspi_inst_t *qspi,
        const uint8_t *src, size_t len)
    {
        // Wait for previous async to complete
        dma_channel_wait_for_finish_blocking(qspi->async_dma_chan);

        qspi_async_inst = qspi;
        qspi->async_busy = true;

        dma_channel_transfer_from_buffer_now(qspi->async_dma_chan, src, len);
    }

    __force_inline static bool psram_qspi_async_is_busy(psram_qspi_inst_t *qspi)
    {
        return dma_channel_is_busy(qspi->async_dma_chan);
    }

    __force_inline static void psram_qspi_async_wait(psram_qspi_inst_t *qspi)
    {
        dma_channel_wait_for_finish_blocking(qspi->async_dma_chan);
        qspi->async_busy = false;
    }
#endif

    // =============================================================================
    // PSRAM Command Buffers (QSPI mode - nibble counts)
    // =============================================================================

    // Write 8 bits: cmd(2) + addr(6) + data(2) = 10 nibbles
    static uint8_t qspi_write8_cmd[] = {
        10,      // 10 nibbles to write
        0,       // 0 nibbles to read
        0x38u,   // Quad Write command
        0, 0, 0, // Address (24-bit)
        0        // Data (8-bit)
    };

    // Read 8 bits: cmd(2) + addr(6) + dummy(6) = 14 nibbles write, 2 nibbles read
    static uint8_t qspi_read8_cmd[] = {
        14,      // 14 nibbles to write
        2,       // 2 nibbles to read
        0xEBu,   // Quad Fast Read command
        0, 0, 0, // Address (24-bit)
        0, 0, 0  // Dummy cycles
    };

    // Write 16 bits: 12 nibbles
    static uint8_t qspi_write16_cmd[] = {
        12,      // 12 nibbles to write
        0,       // 0 nibbles to read
        0x38u,   // Quad Write command
        0, 0, 0, // Address
        0, 0     // Data (16-bit)
    };

    // Read 16 bits: 14 nibbles write, 4 nibbles read
    static uint8_t qspi_read16_cmd[] = {
        14,      // 14 nibbles to write
        4,       // 4 nibbles to read
        0xEBu,   // Quad Fast Read command
        0, 0, 0, // Address
        0, 0, 0  // Dummy cycles
    };

    // Write 32 bits: 16 nibbles
    static uint8_t qspi_write32_cmd[] = {
        16,        // 16 nibbles to write
        0,         // 0 nibbles to read
        0x38u,     // Quad Write command
        0, 0, 0,   // Address
        0, 0, 0, 0 // Data (32-bit)
    };

    // Read 32 bits: 14 nibbles write, 8 nibbles read
    static uint8_t qspi_read32_cmd[] = {
        14,      // 14 nibbles to write
        8,       // 8 nibbles to read
        0xEBu,   // Quad Fast Read command
        0, 0, 0, // Address
        0, 0, 0  // Dummy cycles
    };

    // =============================================================================
    // High-level PSRAM access functions (QSPI mode)
    // =============================================================================

    /**
     * @brief Write 8 bits to PSRAM
     */
    __force_inline static void psram_qspi_write8(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t val)
    {
        qspi_write8_cmd[3] = addr >> 16;
        qspi_write8_cmd[4] = addr >> 8;
        qspi_write8_cmd[5] = addr;
        qspi_write8_cmd[6] = val;
        qspi_write_dma_blocking(qspi, qspi_write8_cmd, sizeof(qspi_write8_cmd));
    }

    /**
     * @brief Read 8 bits from PSRAM
     */
    __force_inline static uint8_t psram_qspi_read8(psram_qspi_inst_t *qspi, uint32_t addr)
    {
        uint8_t val;
        qspi_read8_cmd[3] = addr >> 16;
        qspi_read8_cmd[4] = addr >> 8;
        qspi_read8_cmd[5] = addr;
        qspi_write_read_dma_blocking(qspi, qspi_read8_cmd, sizeof(qspi_read8_cmd), &val, 1);
        return val;
    }

    /**
     * @brief Write 16 bits to PSRAM
     */
    __force_inline static void psram_qspi_write16(psram_qspi_inst_t *qspi, uint32_t addr, uint16_t val)
    {
        qspi_write16_cmd[3] = addr >> 16;
        qspi_write16_cmd[4] = addr >> 8;
        qspi_write16_cmd[5] = addr;
        qspi_write16_cmd[6] = val;
        qspi_write16_cmd[7] = val >> 8;
        qspi_write_dma_blocking(qspi, qspi_write16_cmd, sizeof(qspi_write16_cmd));
    }

    /**
     * @brief Read 16 bits from PSRAM
     */
    __force_inline static uint16_t psram_qspi_read16(psram_qspi_inst_t *qspi, uint32_t addr)
    {
        uint16_t val;
        qspi_read16_cmd[3] = addr >> 16;
        qspi_read16_cmd[4] = addr >> 8;
        qspi_read16_cmd[5] = addr;
        qspi_write_read_dma_blocking(qspi, qspi_read16_cmd, sizeof(qspi_read16_cmd), (uint8_t *)&val, 2);
        return val;
    }

    /**
     * @brief Write 32 bits to PSRAM (blocking)
     */
    __force_inline static void psram_qspi_write32(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t val)
    {
        qspi_write32_cmd[3] = addr >> 16;
        qspi_write32_cmd[4] = addr >> 8;
        qspi_write32_cmd[5] = addr;
        qspi_write32_cmd[6] = val;
        qspi_write32_cmd[7] = val >> 8;
        qspi_write32_cmd[8] = val >> 16;
        qspi_write32_cmd[9] = val >> 24;
        qspi_write_dma_blocking(qspi, qspi_write32_cmd, sizeof(qspi_write32_cmd));
    }

/**
 * @brief Write 32 bits to PSRAM (async)
 */
#if defined(PSRAM_QSPI_ASYNC)
    __force_inline static void psram_qspi_write32_async(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t val)
    {
        qspi_write32_cmd[3] = addr >> 16;
        qspi_write32_cmd[4] = addr >> 8;
        qspi_write32_cmd[5] = addr;
        qspi_write32_cmd[6] = val;
        qspi_write32_cmd[7] = val >> 8;
        qspi_write32_cmd[8] = val >> 16;
        qspi_write32_cmd[9] = val >> 24;
        qspi_write_async(qspi, qspi_write32_cmd, sizeof(qspi_write32_cmd));
    }
#endif

    /**
     * @brief Read 32 bits from PSRAM
     */
    __force_inline static uint32_t psram_qspi_read32(psram_qspi_inst_t *qspi, uint32_t addr)
    {
        uint32_t val;
        qspi_read32_cmd[3] = addr >> 16;
        qspi_read32_cmd[4] = addr >> 8;
        qspi_read32_cmd[5] = addr;
        qspi_write_read_dma_blocking(qspi, qspi_read32_cmd, sizeof(qspi_read32_cmd), (uint8_t *)&val, 4);
        return val;
    }

    // =============================================================================
    // Bulk transfer command buffers
    // =============================================================================
    static uint8_t qspi_write_cmd[6] = {
        0,      // n nibbles to write (set dynamically)
        0,      // 0 nibbles to read
        0x38u,  // Quad Write command
        0, 0, 0 // Address
    };

    static uint8_t qspi_read_cmd[9] = {
        14,      // 14 nibbles to write (header)
        0,       // n nibbles to read (set dynamically)
        0xEBu,   // Quad Fast Read command
        0, 0, 0, // Address
        0, 0, 0  // Dummy cycles
    };

    /**
     * @brief Write buffer to PSRAM
     */
    __force_inline static void psram_qspi_write(psram_qspi_inst_t *qspi, uint32_t addr,
                                                const uint8_t *src, size_t count)
    {
        qspi_write_cmd[0] = (4 + count) * 2; // Convert bytes to nibbles
        qspi_write_cmd[3] = addr >> 16;
        qspi_write_cmd[4] = addr >> 8;
        qspi_write_cmd[5] = addr;
        qspi_write_dma_blocking(qspi, qspi_write_cmd, sizeof(qspi_write_cmd));
        qspi_write_dma_blocking(qspi, src, count);
    }

    /**
     * @brief Read buffer from PSRAM
     */
    __force_inline static void psram_qspi_read(psram_qspi_inst_t *qspi, uint32_t addr,
                                               uint8_t *dst, size_t count)
    {
        qspi_read_cmd[1] = count * 2; // Convert bytes to nibbles
        qspi_read_cmd[3] = addr >> 16;
        qspi_read_cmd[4] = addr >> 8;
        qspi_read_cmd[5] = addr;
        qspi_write_read_dma_blocking(qspi, qspi_read_cmd, sizeof(qspi_read_cmd), dst, count);
    }

    // Async bulk write buffer
    static uint8_t qspi_write_async_buf[134] = {
        0,    // n nibbles
        0,    // 0 read
        0x38u // Quad Write
    };

/**
 * @brief Write buffer to PSRAM (async, max 128 bytes)
 */
#if defined(PSRAM_QSPI_ASYNC)
    __force_inline static void psram_qspi_write_async(psram_qspi_inst_t *qspi, uint32_t addr,
                                                      uint8_t *src, size_t count)
    {
        qspi_write_async_buf[0] = (4 + count) * 2;
        qspi_write_async_buf[3] = addr >> 16;
        qspi_write_async_buf[4] = addr >> 8;
        qspi_write_async_buf[5] = addr;
        memcpy(qspi_write_async_buf + 6, src, count);
        qspi_write_async(qspi, qspi_write_async_buf, 6 + count);
    }
#endif

#ifdef __cplusplus
}
#endif

#endif // _PSRAM_QSPI_H_
