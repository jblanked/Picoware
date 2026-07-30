#include "i2c_bus.h"

#include "board_config.h"

static i2c_master_bus_handle_t s_bus;
static int s_refcount;

esp_err_t v8_i2c_bus_acquire(i2c_master_bus_handle_t *out_bus)
{
    if (out_bus == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    if (s_bus == NULL)
    {
        i2c_master_bus_config_t cfg = {
            .i2c_port = V8_I2C_PORT,
            .sda_io_num = V8_I2C_SDA_GPIO,
            .scl_io_num = V8_I2C_SCL_GPIO,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .flags.enable_internal_pullup = true,
        };

        esp_err_t err = i2c_new_master_bus(&cfg, &s_bus);
        if (err != ESP_OK)
        {
            s_bus = NULL;
            return err;
        }
    }

    ++s_refcount;
    *out_bus = s_bus;
    return ESP_OK;
}

void v8_i2c_bus_release(void)
{
    if (s_refcount == 0)
    {
        return;
    }

    if (--s_refcount == 0 && s_bus != NULL)
    {
        i2c_del_master_bus(s_bus);
        s_bus = NULL;
    }
}

esp_err_t v8_i2c_add_device(uint16_t address, i2c_master_dev_handle_t *out_dev)
{
    if (out_dev == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    i2c_master_bus_handle_t bus = NULL;
    esp_err_t err = v8_i2c_bus_acquire(&bus);
    if (err != ESP_OK)
    {
        return err;
    }

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = address,
        .scl_speed_hz = V8_I2C_FREQ_HZ,
    };

    err = i2c_master_bus_add_device(bus, &dev_cfg, out_dev);
    if (err != ESP_OK)
    {
        v8_i2c_bus_release();
    }

    return err;
}
