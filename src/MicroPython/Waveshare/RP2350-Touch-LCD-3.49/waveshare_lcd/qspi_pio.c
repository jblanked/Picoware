/*****************************************************************************
* | File      	:   qspi_pio.c
* | Author      :   Waveshare Team
* | Function    :   QSPI Interface Functions
* | Info        :
*----------------
* |	This version:   V1.0
* | Date        :   2025-03-20
* | Info        :
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of theex Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
******************************************************************************/
#include "qspi_pio.h"
#include "pico/stdlib.h"
pio_qspi_t qspi = {
    .pio = pio0,
    .sm = 0,
    .sm_4wire = 0,
    .sm_1wire = 1,
    .pin_cs = PIN_CS,
    .pin_sclk = PIN_SCLK,
    .pin_dio0 = PIN_DIO0,
    .pin_dio1 = PIN_DIO1,
    .pin_dio2 = PIN_DIO2,
    .pin_dio3 = PIN_DIO3,
    .pin_pwr_en = PIN_PWR_EN,
    .pin_rst = PIN_RST};

/******************************************************************************
function : QSPI related GPIO initialization
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_GPIO_Init(pio_qspi_t qspi)
{
    gpio_init(qspi.pin_cs);
    gpio_pull_down(qspi.pin_cs);
    gpio_set_dir(qspi.pin_cs, GPIO_OUT);
    gpio_put(qspi.pin_cs, 1);

    gpio_init(qspi.pin_pwr_en);
    gpio_set_dir(qspi.pin_pwr_en, GPIO_OUT);
    gpio_put(qspi.pin_pwr_en, 1);

    gpio_init(qspi.pin_rst);
    gpio_set_dir(qspi.pin_rst, GPIO_OUT);
}

/******************************************************************************
function : QSPI Select
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_Select(pio_qspi_t qspi)
{
    gpio_put(qspi.pin_cs, 0);
}

/******************************************************************************
function : QSPI Deselect
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_Deselect(pio_qspi_t qspi)
{
    gpio_put(qspi.pin_cs, 1);
}

/******************************************************************************
function : QSPI PIO initialization
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_PIO_Init(pio_qspi_t qspi)
{
    uint offset = pio_add_program(qspi.pio, &qspi_4wire_data_program);
    qspi_4wire_data_program_init(qspi.pio, qspi.sm_4wire, offset, PIN_SCLK, PIN_DIO0, 4);

    // offset = pio_add_program(qspi.pio, &qspi_1write_cmd_program);
    // qspi_1write_cmd_program_init(qspi.pio, qspi.sm_1wire, offset, PIN_SCLK, PIN_DIO0, 1);
    // pio_sm_clear_fifos(qspi.pio, qspi.sm_1wire);

    pio_sm_set_enabled(qspi.pio, qspi.sm_4wire, false);
    pio_sm_set_enabled(qspi.pio, qspi.sm_1wire, false);
}

/******************************************************************************
function : QSPI PIO one-line mode, generally used to send commands
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_1Wrie_Mode(pio_qspi_t *qspi)
{
    pio_sm_set_enabled(qspi->pio, qspi->sm_4wire, false);
    pio_sm_set_enabled(qspi->pio, qspi->sm_1wire, true);
    qspi->sm = qspi->sm_1wire;
}

/******************************************************************************
function : QSPI PIO four-wire mode, generally used to send data
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_4Wrie_Mode(pio_qspi_t *qspi)
{
    pio_sm_set_enabled(qspi->pio, qspi->sm_4wire, true);
    pio_sm_set_enabled(qspi->pio, qspi->sm_1wire, false);
    qspi->sm = qspi->sm_4wire;
}

/******************************************************************************
function : QSPI PIO sends data
parameter:
    qspi : QSPI structure
******************************************************************************/
static void QSPI_PIO_Write(pio_qspi_t qspi, uint32_t val)
{
    pio_sm_put_blocking(qspi.pio, qspi.sm, val << 24);
}

/******************************************************************************
function : QSPI PIO 1-wire mode sends data
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_DATA_Write(pio_qspi_t qspi, uint32_t val)
{
    // QSPI_PIO_Write(qspi,val);
    uint8_t cmd_buf[4];
    // uint8_t buf_temp;
    for (int i = 0; i < 4; ++i)
    {
        uint8_t bit1 = (val & (1 << (2 * i))) ? 1 : 0;
        uint8_t bit2 = (val & (1 << (2 * i + 1))) ? 1 : 0;
        cmd_buf[3 - i] = bit1 | (bit2 << 4);
    }

    for (int i = 0; i < 4; i++)
    {
        QSPI_PIO_Write(qspi, cmd_buf[i]);
    }
}

/******************************************************************************
function : QSPI PIO 1-wire mode sends data
parameter:
    qspi : QSPI structure
******************************************************************************/
void QSPI_CMD_Write(pio_qspi_t qspi, uint32_t val)
{
    // QSPI_PIO_Write(qspi,val);
    uint8_t cmd_buf[4];
    // uint8_t buf_temp;
    for (int i = 0; i < 4; ++i)
    {
        uint8_t bit1 = (val & (1 << (2 * i))) ? 1 : 0;
        uint8_t bit2 = (val & (1 << (2 * i + 1))) ? 1 : 0;
        cmd_buf[3 - i] = bit1 | (bit2 << 4);
    }

    for (int i = 0; i < 4; i++)
    {
        QSPI_PIO_Write(qspi, cmd_buf[i]);
    }
}

/******************************************************************************
function : QSPI PIO 1-wire mode configuration register
parameter:
    qspi : QSPI structure
    addr : Register address
******************************************************************************/
void QSPI_REGISTER_Write(pio_qspi_t qspi, uint32_t addr)
{
    // 1 WIRE CMD
    QSPI_CMD_Write(qspi, 0x02);

    // 1 WIRE ADDR
    QSPI_DATA_Write(qspi, 0x00);
    QSPI_DATA_Write(qspi, addr);
    QSPI_DATA_Write(qspi, 0x00);
    // WAIT_TIME();
}

/******************************************************************************
function : QSPI RGB pixel interface one line to send address
parameter:
    qspi : QSPI structure
    addr : RGB pixel interface register address
******************************************************************************/
void QSPI_Pixel_Write(pio_qspi_t qspi, uint32_t addr)
{
    // 1 WIRE CMD
    QSPI_CMD_Write(qspi, 0x32);

    // 1 WIRE ADDR
    QSPI_DATA_Write(qspi, 0x00);
    QSPI_DATA_Write(qspi, addr);
    QSPI_DATA_Write(qspi, 0x00);
    // WAIT_TIME();
}
