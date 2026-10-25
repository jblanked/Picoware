/******************************************************************************
 * picoware-psram QSPI Interface Header
 *
 * Enhanced QSPI driver for PSRAM inspired by Waveshare implementation
 * Provides high-speed 4-wire transfers with DMA support
 *
 * Copyright © 2023 Ian Scott (original SPI implementation)
 * Copyright © 2025 JBlanked (QSPI implementation)
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
     * @param clkdiv Requested PIO divider; clamped to at least 4.0 for data integrity
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
    static void __time_critical_func(qspi_write_dma_blocking)(
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
    static void __time_critical_func(qspi_write_read_dma_blocking)(
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
    static void __time_critical_func(qspi_write_async)(
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

    // Local commands, one lock per complete transaction. Also compiled by host tests.
#define PSRAM_TRANSFER_MAX 120u
static inline void psram_qspi_write(psram_qspi_inst_t *qspi, uint32_t addr,
                                   const uint8_t *src, size_t count)
{
    while (count) {
        size_t n = count > PSRAM_TRANSFER_MAX ? PSRAM_TRANSFER_MAX : count;
        uint8_t cmd[6 + PSRAM_TRANSFER_MAX] = {0,0,0x38,0,0,0};
        cmd[0]=(uint8_t)((4+n)*2);cmd[3]=addr>>16;cmd[4]=addr>>8;cmd[5]=addr;
        memcpy(cmd+6,src,n);
        qspi_write_dma_blocking(qspi,cmd,6+n);
        addr+=n;src+=n;count-=n;
    }
}
static inline void psram_qspi_read(psram_qspi_inst_t *qspi, uint32_t addr,
                                  uint8_t *dst, size_t count)
{
    while (count) {
        size_t n = count > PSRAM_TRANSFER_MAX ? PSRAM_TRANSFER_MAX : count;
        uint8_t cmd[9]={14,(uint8_t)(n*2),0xeb,(uint8_t)(addr>>16),(uint8_t)(addr>>8),(uint8_t)addr,0,0,0};
        qspi_write_read_dma_blocking(qspi,cmd,sizeof(cmd),dst,n);
        addr+=n;dst+=n;count-=n;
    }
}
static inline void psram_qspi_write8(psram_qspi_inst_t *qspi,uint32_t addr,uint8_t v)
{psram_qspi_write(qspi,addr,&v,1);}
static inline uint8_t psram_qspi_read8(psram_qspi_inst_t *qspi,uint32_t addr)
{uint8_t v;psram_qspi_read(qspi,addr,&v,1);return v;}
static inline void psram_qspi_write16(psram_qspi_inst_t *qspi,uint32_t addr,uint16_t v)
{uint8_t b[2]={(uint8_t)v,(uint8_t)(v>>8)};psram_qspi_write(qspi,addr,b,2);}
static inline uint16_t psram_qspi_read16(psram_qspi_inst_t *qspi,uint32_t addr)
{uint8_t b[2];psram_qspi_read(qspi,addr,b,2);return (uint16_t)b[0]|((uint16_t)b[1]<<8);}
static inline void psram_qspi_write32(psram_qspi_inst_t *qspi,uint32_t addr,uint32_t v)
{uint8_t b[4]={(uint8_t)v,(uint8_t)(v>>8),(uint8_t)(v>>16),(uint8_t)(v>>24)};psram_qspi_write(qspi,addr,b,4);}
static inline uint32_t psram_qspi_read32(psram_qspi_inst_t *qspi,uint32_t addr)
{uint8_t b[4];psram_qspi_read(qspi,addr,b,4);return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
#if defined(PSRAM_QSPI_ASYNC)
// No in-tree caller requires deferred completion. Complete before returning so
// stack commands and caller buffers cannot outlive their ownership.
static inline void psram_qspi_write32_async(psram_qspi_inst_t *qspi,uint32_t addr,uint32_t v)
{psram_qspi_write32(qspi,addr,v);}
static inline void psram_qspi_write_async(psram_qspi_inst_t *qspi,uint32_t addr,uint8_t *src,size_t count)
{psram_qspi_write(qspi,addr,src,count);}
#endif


#ifdef __cplusplus
}
#endif

#endif // _PSRAM_QSPI_H_
