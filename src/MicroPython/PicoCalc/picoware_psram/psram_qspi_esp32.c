#include "picoware_psram_shared.h"
#include "picocalc_spi_bus.h"

#include "../ESP32_P4/board_config.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "py/runtime.h"

static const char *TAG = "picocalc-psram";

static bool psram_range_valid(const psram_qspi_inst_t *qspi, uint32_t addr, size_t count)
{
    if (qspi == NULL || qspi->device == NULL || addr > qspi->size || count > qspi->size - addr)
    {
        ESP_LOGE(TAG, "PSRAM access out of range (address=%lu, length=%u)",
                 (unsigned long)addr, (unsigned)count);
        return false;
    }
    return true;
}

static esp_err_t psram_send_spi_command(psram_qspi_inst_t *qspi, uint8_t command)
{
    spi_transaction_t transaction = {
        .length = 8,
        .tx_buffer = &command,
    };
    return spi_device_polling_transmit(qspi->device, &transaction);
}

static esp_err_t psram_send_qpi_command(psram_qspi_inst_t *qspi, uint8_t command)
{
    spi_transaction_t transaction = {
        .flags = SPI_TRANS_MODE_QIO,
        .length = 8,
        .tx_buffer = &command,
    };
    return spi_device_polling_transmit(qspi->device, &transaction);
}

static esp_err_t psram_write_qio(psram_qspi_inst_t *qspi, uint32_t addr, const uint8_t *src, size_t count)
{
    spi_transaction_ext_t transaction = {0};
    transaction.base.flags = SPI_TRANS_MODE_QIO |
                             SPI_TRANS_MULTILINE_CMD |
                             SPI_TRANS_MULTILINE_ADDR |
                             SPI_TRANS_VARIABLE_CMD |
                             SPI_TRANS_VARIABLE_ADDR;
    transaction.base.cmd = 0x38;
    transaction.base.addr = addr;
    transaction.base.length = count * 8;
    transaction.base.tx_buffer = src;
    transaction.command_bits = 8;
    transaction.address_bits = 24;
    return spi_device_polling_transmit(qspi->device, &transaction.base);
}

static esp_err_t psram_read_qio(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t *dst, size_t count)
{
    spi_transaction_ext_t transaction = {0};
    transaction.base.flags = SPI_TRANS_MODE_QIO |
                             SPI_TRANS_MULTILINE_CMD |
                             SPI_TRANS_MULTILINE_ADDR |
                             SPI_TRANS_VARIABLE_CMD |
                             SPI_TRANS_VARIABLE_ADDR |
                             SPI_TRANS_VARIABLE_DUMMY;
    transaction.base.cmd = 0xEB;
    transaction.base.addr = addr;
    transaction.base.rxlength = count * 8;
    transaction.base.rx_buffer = dst;
    transaction.command_bits = 8;
    transaction.address_bits = 24;
    transaction.dummy_bits = 6;
    return spi_device_polling_transmit(qspi->device, &transaction.base);
}

static void psram_raise_init_error(const char *operation, esp_err_t err)
{
    ESP_LOGE(TAG, "%s failed: %s", operation, esp_err_to_name(err));
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("failed to initialize PicoCalc external PSRAM"));
}

psram_qspi_inst_t psram_qspi_init(void *unused, int sm, float clkdiv)
{
    (void)unused;
    (void)sm;
    (void)clkdiv;

    esp_err_t err = picocalc_spi_bus_init();
    if (err != ESP_OK)
    {
        psram_raise_init_error("SPI2 bus initialization", err);
    }

    psram_qspi_inst_t qspi = {
        .device = NULL,
        .size = PSRAM_SIZE,
        .async_busy = false,
    };
    spi_device_interface_config_t device_config = {
        .clock_speed_hz = 20000000,
        .mode = 0,
        .spics_io_num = PICOCALC_PSRAM_CS_GPIO,
        .queue_size = 1,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    err = spi_bus_add_device(SPI2_HOST, &device_config, &qspi.device);
    if (err != ESP_OK)
    {
        psram_raise_init_error("PSRAM SPI device setup", err);
    }

    // A previous soft reset can leave the external RAM in QPI mode.
    err = psram_send_qpi_command(&qspi, 0xF5);
    if (err == ESP_OK)
    {
        esp_rom_delay_us(50);
    }
    if (err == ESP_OK)
    {
        err = psram_send_spi_command(&qspi, 0x66);
    }
    if (err == ESP_OK)
    {
        esp_rom_delay_us(50);
        err = psram_send_spi_command(&qspi, 0x99);
    }
    if (err == ESP_OK)
    {
        esp_rom_delay_us(100);
        err = psram_send_spi_command(&qspi, 0x35);
    }
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "PSRAM QPI initialization failed: %s", esp_err_to_name(err));
        esp_err_t remove_err = spi_bus_remove_device(qspi.device);
        if (remove_err != ESP_OK)
        {
            ESP_LOGE(TAG, "PSRAM SPI device cleanup failed: %s", esp_err_to_name(remove_err));
        }
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("failed to initialize PicoCalc external PSRAM"));
    }
    esp_rom_delay_us(100);
    return qspi;
}

void psram_qspi_deinit(psram_qspi_inst_t *qspi)
{
    if (qspi != NULL && qspi->device != NULL)
    {
        esp_err_t err = spi_bus_remove_device(qspi->device);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PSRAM SPI device removal failed: %s", esp_err_to_name(err));
            return;
        }
        qspi->device = NULL;
        qspi->size = 0;
        qspi->async_busy = false;
    }
}

void psram_qspi_write(psram_qspi_inst_t *qspi, uint32_t addr, const uint8_t *src, size_t count)
{
    if (count == 0)
    {
        return;
    }
    if (src == NULL)
    {
        ESP_LOGE(TAG, "PSRAM write received a null source buffer");
        return;
    }
    if (!psram_range_valid(qspi, addr, count))
    {
        return;
    }

    while (count != 0)
    {
        size_t chunk = count > PSRAM_CHUNK_SIZE ? PSRAM_CHUNK_SIZE : count;
        esp_err_t err = psram_write_qio(qspi, addr, src, chunk);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PSRAM write failed at %lu: %s", (unsigned long)addr, esp_err_to_name(err));
            return;
        }
        addr += chunk;
        src += chunk;
        count -= chunk;
    }
}

void psram_qspi_read(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t *dst, size_t count)
{
    if (count == 0)
    {
        return;
    }
    if (dst == NULL)
    {
        ESP_LOGE(TAG, "PSRAM read received a null destination buffer");
        return;
    }
    if (!psram_range_valid(qspi, addr, count))
    {
        return;
    }

    while (count != 0)
    {
        size_t chunk = count > PSRAM_CHUNK_SIZE ? PSRAM_CHUNK_SIZE : count;
        esp_err_t err = psram_read_qio(qspi, addr, dst, chunk);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PSRAM read failed at %lu: %s", (unsigned long)addr, esp_err_to_name(err));
            return;
        }
        addr += chunk;
        dst += chunk;
        count -= chunk;
    }
}

void psram_qspi_write8(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t value)
{
    psram_qspi_write(qspi, addr, &value, sizeof(value));
}

uint8_t psram_qspi_read8(psram_qspi_inst_t *qspi, uint32_t addr)
{
    uint8_t value = 0;
    psram_qspi_read(qspi, addr, &value, sizeof(value));
    return value;
}

void psram_qspi_write16(psram_qspi_inst_t *qspi, uint32_t addr, uint16_t value)
{
    psram_qspi_write(qspi, addr, (const uint8_t *)&value, sizeof(value));
}

uint16_t psram_qspi_read16(psram_qspi_inst_t *qspi, uint32_t addr)
{
    uint16_t value = 0;
    psram_qspi_read(qspi, addr, (uint8_t *)&value, sizeof(value));
    return value;
}

void psram_qspi_write32(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t value)
{
    psram_qspi_write(qspi, addr, (const uint8_t *)&value, sizeof(value));
}

uint32_t psram_qspi_read32(psram_qspi_inst_t *qspi, uint32_t addr)
{
    uint32_t value = 0;
    psram_qspi_read(qspi, addr, (uint8_t *)&value, sizeof(value));
    return value;
}

void psram_qspi_write32_async(psram_qspi_inst_t *qspi, uint32_t addr, uint32_t value)
{
    psram_qspi_write32(qspi, addr, value);
}

bool psram_qspi_async_is_busy(psram_qspi_inst_t *qspi)
{
    return qspi != NULL && qspi->async_busy;
}

void psram_qspi_async_wait(psram_qspi_inst_t *qspi)
{
    if (qspi != NULL)
    {
        qspi->async_busy = false;
    }
}

void psram_qspi_write_async(psram_qspi_inst_t *qspi, uint32_t addr, uint8_t *src, size_t count)
{
    psram_qspi_write(qspi, addr, src, count);
}

int psram_qspi_test(psram_qspi_inst_t *qspi)
{
    const uint8_t test_value = 0xA5;
    const uint32_t test_address = 0x1000;
    psram_qspi_write8(qspi, test_address, test_value);
    if (psram_qspi_read8(qspi, test_address) != test_value)
    {
        return -1;
    }

    const uint32_t test_value32 = 0xDEADBEEF;
    psram_qspi_write32(qspi, test_address + 4, test_value32);
    return psram_qspi_read32(qspi, test_address + 4) == test_value32 ? 0 : -2;
}
