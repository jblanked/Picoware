
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/pio.h"

#include "pico/platform.h"
#include "pio_qspi.h"
#include "pio_qspi.pio.h"

#include "pico/stdlib.h"
#include <stdio.h>

static uint pio_qspi_sm;

static int pio_qspi_dma_chan;

static inline void qspi_program_init(PIO pio, uint sm, uint offset, uint sclk_pin, uint d0_pin, float div)
{

    // creates state machine configuration object c, sets
    // to default configurations. I believe this function is auto-generated
    // and gets a name of <program name>_program_get_default_config
    pio_sm_config c = qspi_program_get_default_config(offset);

    // Join the TX FIFO to the state machine's TX FIFO
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);

    // Map the state machine's SET pin group to one pin, namely the `pin`
    // parameter to this function.
    sm_config_set_sideset_pins(&c, sclk_pin);

    // Set clock division (div by 5 for 25 MHz state machine)
    sm_config_set_clkdiv(&c, div);

    // Set this pin's GPIO function (connect PIO to the pad)
    pio_gpio_init(pio, sclk_pin);
    pio_gpio_init(pio, d0_pin + 0);
    pio_gpio_init(pio, d0_pin + 1);
    pio_gpio_init(pio, d0_pin + 2);
    pio_gpio_init(pio, d0_pin + 3);

    gpio_pull_up(sclk_pin);
    gpio_pull_up(d0_pin + 0);
    gpio_pull_up(d0_pin + 1);
    gpio_pull_up(d0_pin + 2);
    gpio_pull_up(d0_pin + 3);

    // Set the pin direction to output at the PIO
    pio_sm_set_consecutive_pindirs(pio, sm, sclk_pin, 1, true);

    // pio_sm_set_consecutive_pindirs(pio, sm, d0_pin, 1, true);
    pio_sm_set_consecutive_pindirs(pio, sm, d0_pin, 4, true);

    // Set the output pins
    sm_config_set_out_pins(&c, d0_pin, 4);

    sm_config_set_out_shift(&c, false, true, 8);

    // Load our configuration, and jump to the start of the program
    pio_sm_init(pio, sm, offset, &c);

    // Set the state machine running
    pio_sm_set_enabled(pio, sm, true);
}

void pio_qspi_dma_init(void)
{
    pio_qspi_dma_chan = dma_claim_unused_channel(true);
    dma_channel_config c0 = dma_channel_get_default_config(pio_qspi_dma_chan);
    channel_config_set_transfer_data_size(&c0, DMA_SIZE_8); // 16-bit transfers

    channel_config_set_read_increment(&c0, true);
    channel_config_set_write_increment(&c0, false);
    channel_config_set_dreq(&c0, pio_get_dreq(QSPI_PIO, pio_qspi_sm, true));

    dma_channel_configure(
        pio_qspi_dma_chan,
        &c0,
        &QSPI_PIO->txf[pio_qspi_sm], // TX FIFO
        NULL,                        // frame buffer
        0,                           // size of frame buffer
        false);
}

void pio_qspi_1bit_write_blocking(uint8_t buf)
{
    uint8_t cmd_buf[4];
    for (int i = 0; i < 4; ++i)
    {
        uint8_t bit1 = (buf & (1 << (2 * i))) ? 1 : 0;
        uint8_t bit2 = (buf & (1 << (2 * i + 1))) ? 1 : 0;
        cmd_buf[3 - i] = bit1 | (bit2 << 4);
    }
    for (int i = 0; i < 4; i++)
    {
        while (pio_sm_is_tx_fifo_full(QSPI_PIO, pio_qspi_sm))
            tight_loop_contents();
        *(volatile uint8_t *)&(QSPI_PIO->txf[pio_qspi_sm]) = cmd_buf[i];
    }
}

void pio_qspi_1bit_write_data_blocking(uint8_t *buf, size_t len)
{

    uint8_t cmd_buf[4 * len];

    for (int j = 0; j < len; j++)
    {
        for (int i = 0; i < 4; i++)
        {
            uint8_t bit1 = (buf[j] & (1 << (2 * i))) ? 1 : 0;
            uint8_t bit2 = (buf[j] & (1 << (2 * i + 1))) ? 1 : 0;
            cmd_buf[j * 4 + 3 - i] = bit1 | (bit2 << 4);
        }
    }

    for (int i = 0; i < 4 * len; i++)
    {
        while (pio_sm_is_tx_fifo_full(QSPI_PIO, pio_qspi_sm))
            tight_loop_contents();
        *(volatile uint8_t *)&(QSPI_PIO->txf[pio_qspi_sm]) = cmd_buf[i];
        // pio_sm_put_blocking(QSPI_PIO, pio_qspi_sm, cmd_buf[3 - i]);
    }
    while (pio_sm_is_tx_fifo_full(QSPI_PIO, pio_qspi_sm))
        tight_loop_contents();
}

void pio_qspi_4bit_write_data_blocking(uint8_t *buf, size_t len)
{
    for (size_t i = 0; i < len; i++)
    {
        while (pio_sm_is_tx_fifo_full(QSPI_PIO, pio_qspi_sm))
            tight_loop_contents();
        *(volatile uint8_t *)&(QSPI_PIO->txf[pio_qspi_sm]) = buf[i];
    }
}

void pio_qspi_1bit_write_data(uint8_t *buf, size_t len)
{
    uint8_t cmd_buf[4 * len];

    for (int j = 0; j < len; j++)
    {
        for (int i = 0; i < 4; i++)
        {
            uint8_t bit1 = (buf[j] & (1 << (2 * i))) ? 1 : 0;
            uint8_t bit2 = (buf[j] & (1 << (2 * i + 1))) ? 1 : 0;
            cmd_buf[j * 4 + 3 - i] = bit1 | (bit2 << 4);
        }
    }
    dma_channel_set_trans_count(pio_qspi_dma_chan, 4 * len, true);
    dma_channel_set_read_addr(pio_qspi_dma_chan, cmd_buf, true);
}

void pio_qspi_4bit_write_data(uint8_t *buf, size_t len)
{
    dma_channel_set_trans_count(pio_qspi_dma_chan, len, true);
    dma_channel_set_read_addr(pio_qspi_dma_chan, buf, true);
}

int pio_qspi_get_dma_channel(void)
{
    return pio_qspi_dma_chan;
}

uint pio_qspi_get_sm(void)
{
    return pio_qspi_sm;
}

void pio_qspi_init(uint sclk_pin, uint d0_pin, uint32_t baudrate, channel_irq_callback_t irq_cb)
{
    float div = (float)clock_get_hz(clk_sys) / (float)baudrate / 2;
    if (div < 1.0f)
        div = 1.0f;

    // Claim a free state machine on a PIO instance
    pio_qspi_sm = pio_claim_unused_sm(QSPI_PIO, true);

    // Load the program into the PIO instance
    uint pio_qspi_offset = pio_add_program(QSPI_PIO, &qspi_program);

    // Initialize the state machine with the program
    qspi_program_init(QSPI_PIO, pio_qspi_sm, pio_qspi_offset, sclk_pin, d0_pin, div);

    pio_qspi_dma_init();

    if (irq_cb != NULL)
    {
        bsp_dma_channel_irq_add(1, pio_qspi_dma_chan, irq_cb);
    }
}