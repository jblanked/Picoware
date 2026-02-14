/******************************************************************************
 * picoware-psram QSPI Implementation
 *
 * Enhanced QSPI driver for PSRAM inspired by Waveshare implementation
 *
 * Copyright © 2023 Ian Scott (original SPI implementation)
 * Copyright © 2025 JBlanked (enhanced QSPI implementation)
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

#include "psram_qspi.h"
#include "pico/stdlib.h"
#include <stdio.h>

// Global async instance pointer
#if defined(PSRAM_QSPI_ASYNC)
psram_qspi_inst_t *qspi_async_inst = NULL;
#endif

/**
 * @brief Initialize PSRAM in SPI mode first, then switch to QSPI
 */
static void psram_send_spi_command(psram_qspi_inst_t *qspi, uint8_t cmd)
{
    // For initial SPI commands, we need to bit-bang or use a simple approach
    // Since PIO is set up for QSPI, we'll use direct GPIO manipulation

    uint pin_cs = qspi->pin_cs;
    uint pin_sck = qspi->pin_sck;
    uint pin_sio0 = qspi->pin_sio0;

    // Disable PIO temporarily
    pio_sm_set_enabled(qspi->pio, qspi->sm, false);

    // Set pins to GPIO mode
    gpio_init(pin_cs);
    gpio_init(pin_sck);
    gpio_init(pin_sio0);
    gpio_set_dir(pin_cs, GPIO_OUT);
    gpio_set_dir(pin_sck, GPIO_OUT);
    gpio_set_dir(pin_sio0, GPIO_OUT);

    // CS low
    gpio_put(pin_cs, 0);

    // Send command byte (MSB first)
    for (int i = 7; i >= 0; i--)
    {
        gpio_put(pin_sio0, (cmd >> i) & 1);
        gpio_put(pin_sck, 0);
        busy_wait_us(1);
        gpio_put(pin_sck, 1);
        busy_wait_us(1);
    }

    // CS high
    gpio_put(pin_sck, 0);
    gpio_put(pin_cs, 1);

    // Re-enable PIO control
    pio_gpio_init(qspi->pio, pin_cs);
    pio_gpio_init(qspi->pio, pin_sck);
    pio_gpio_init(qspi->pio, pin_sio0);

    pio_sm_set_enabled(qspi->pio, qspi->sm, true);
}

/**
 * @brief Send a single-byte command while in QPI mode
 */
static void psram_send_qpi_command(psram_qspi_inst_t *qspi, uint8_t cmd)
{
    // QSPI PIO protocol: [nibbles_to_write, nibbles_to_read, cmd]
    uint8_t qpi_cmd[] = {
        2, // 2 nibbles (1 byte) to write
        0, // 0 nibbles to read
        cmd};
    qspi_write_dma_blocking(qspi, qpi_cmd, sizeof(qpi_cmd));
}

/**
 * @brief Initialize PSRAM QSPI interface
 */
psram_qspi_inst_t psram_qspi_init(PIO pio, int sm, float clkdiv)
{
    psram_qspi_inst_t qspi;

    qspi.pio = pio;
    qspi.clkdiv = clkdiv;
    qspi.pin_cs = PSRAM_QSPI_PIN_CS;
    qspi.pin_sck = PSRAM_QSPI_PIN_SCK;
    qspi.pin_sio0 = PSRAM_QSPI_PIN_SIO0;

    // Claim state machine
    if (sm == -1)
    {
        qspi.sm = pio_claim_unused_sm(pio, true);
    }
    else
    {
        qspi.sm = sm;
        pio_sm_claim(pio, sm);
    }

#if defined(PSRAM_QSPI_SPINLOCK)
    int spin_id = spin_lock_claim_unused(true);
    qspi.spinlock = spin_lock_init(spin_id);
#endif

    // Configure GPIO drive strength and slew rate for high-speed operation
    gpio_set_drive_strength(qspi.pin_cs, GPIO_DRIVE_STRENGTH_8MA);
    gpio_set_drive_strength(qspi.pin_sck, GPIO_DRIVE_STRENGTH_8MA);
    gpio_set_slew_rate(qspi.pin_cs, GPIO_SLEW_RATE_FAST);
    gpio_set_slew_rate(qspi.pin_sck, GPIO_SLEW_RATE_FAST);

    for (uint i = 0; i < 4; i++)
    {
        gpio_set_drive_strength(qspi.pin_sio0 + i, GPIO_DRIVE_STRENGTH_8MA);
        gpio_set_slew_rate(qspi.pin_sio0 + i, GPIO_SLEW_RATE_FAST);
        gpio_set_input_hysteresis_enabled(qspi.pin_sio0 + i, false);
    }

    // Load PIO program
    qspi.offset = pio_add_program(pio, &qspi_psram_rw_program);

    // Initialize PIO state machine
    qspi_psram_rw_program_init(pio, qspi.sm, qspi.offset, 8, clkdiv,
                               qspi.pin_cs, qspi.pin_sio0);

#if defined(PSRAM_QSPI_USE_DMA)
    // Write DMA channel
    qspi.write_dma_chan = dma_claim_unused_channel(true);
    qspi.write_dma_cfg = dma_channel_get_default_config(qspi.write_dma_chan);
    channel_config_set_transfer_data_size(&qspi.write_dma_cfg, DMA_SIZE_8);
    channel_config_set_read_increment(&qspi.write_dma_cfg, true);
    channel_config_set_write_increment(&qspi.write_dma_cfg, false);
    channel_config_set_dreq(&qspi.write_dma_cfg, pio_get_dreq(pio, qspi.sm, true));
    dma_channel_set_write_addr(qspi.write_dma_chan, &pio->txf[qspi.sm], false);
    dma_channel_set_config(qspi.write_dma_chan, &qspi.write_dma_cfg, false);

    // Read DMA channel
    qspi.read_dma_chan = dma_claim_unused_channel(true);
    qspi.read_dma_cfg = dma_channel_get_default_config(qspi.read_dma_chan);
    channel_config_set_transfer_data_size(&qspi.read_dma_cfg, DMA_SIZE_8);
    channel_config_set_read_increment(&qspi.read_dma_cfg, false);
    channel_config_set_write_increment(&qspi.read_dma_cfg, true);
    channel_config_set_dreq(&qspi.read_dma_cfg, pio_get_dreq(pio, qspi.sm, false));
    dma_channel_set_read_addr(qspi.read_dma_chan, &pio->rxf[qspi.sm], false);
    dma_channel_set_config(qspi.read_dma_chan, &qspi.read_dma_cfg, false);
#endif

#if defined(PSRAM_QSPI_ASYNC)
    // Async DMA channel
    qspi.async_dma_chan = dma_claim_unused_channel(true);
    qspi.async_dma_cfg = dma_channel_get_default_config(qspi.async_dma_chan);
    channel_config_set_transfer_data_size(&qspi.async_dma_cfg, DMA_SIZE_8);
    channel_config_set_read_increment(&qspi.async_dma_cfg, true);
    channel_config_set_write_increment(&qspi.async_dma_cfg, false);
    channel_config_set_dreq(&qspi.async_dma_cfg, pio_get_dreq(pio, qspi.sm, true));
    dma_channel_set_write_addr(qspi.async_dma_chan, &pio->txf[qspi.sm], false);
    dma_channel_set_config(qspi.async_dma_chan, &qspi.async_dma_cfg, false);
    qspi.async_busy = false;
#endif

    // Reset PSRAM (SPI mode commands)
    psram_send_spi_command(&qspi, 0x66); // Reset Enable
    busy_wait_us(50);
    psram_send_spi_command(&qspi, 0x99); // Reset
    busy_wait_us(100);

    // Enter QPI mode
    psram_send_spi_command(&qspi, 0x35); // Enter QPI
    busy_wait_us(100);

    return qspi;
}

/**
 * @brief Deinitialize PSRAM QSPI interface
 */
void psram_qspi_deinit(psram_qspi_inst_t *qspi)
{
#if defined(PSRAM_QSPI_ASYNC)
    if (qspi->async_busy)
    {
        psram_qspi_async_wait(qspi);
    }
    // Async DMA channel teardown
    dma_channel_unclaim(qspi->async_dma_chan);
#endif

#if defined(PSRAM_QSPI_USE_DMA)
    // Write DMA channel teardown
    dma_channel_unclaim(qspi->write_dma_chan);
    // Read DMA channel teardown
    dma_channel_unclaim(qspi->read_dma_chan);
#endif

#if defined(PSRAM_QSPI_SPINLOCK)
    int spin_id = spin_lock_get_num(qspi->spinlock);
    spin_lock_unclaim(spin_id);
#endif

    // Unclaim state machine
    pio_sm_unclaim(qspi->pio, qspi->sm);

    // Exit QPI mode before removing the program
    uint8_t psram_qpi_exit_cmd[] = {2, 0, 0xF5};
    qspi_write_dma_blocking(qspi, psram_qpi_exit_cmd, 3);
    busy_wait_us(50);

    // Remove PIO program
    pio_remove_program(qspi->pio, &qspi_psram_rw_program, qspi->offset);
}

/**
 * @brief Test PSRAM functionality
 */
int psram_qspi_test(psram_qspi_inst_t *qspi)
{
    // Write test pattern
    uint8_t test_val = 0xA5;
    uint32_t test_addr = 0x1000;

    psram_qspi_write8(qspi, test_addr, test_val);
    busy_wait_us(10);

    uint8_t read_val = psram_qspi_read8(qspi, test_addr);

    if (read_val != test_val)
    {
        return -1; // Test failed
    }

    // Test 32-bit
    uint32_t test_val32 = 0xDEADBEEF;
    psram_qspi_write32(qspi, test_addr + 4, test_val32);
    busy_wait_us(10);

    uint32_t read_val32 = psram_qspi_read32(qspi, test_addr + 4);

    if (read_val32 != test_val32)
    {
        return -2; // Test failed
    }

    return 0; // Success
}
