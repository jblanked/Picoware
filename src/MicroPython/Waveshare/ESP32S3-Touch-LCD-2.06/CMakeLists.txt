set(waveshare_watch_src_sources
    "i2c/i2c_bus.c"
    "lcd/lcd.c"
    "audio/audio.c"
    "sd/sdcard.c"
    "sd/storage.c"
    "touch/touch.c"
    "battery/battery.c"
    "ir/ir.c"
)

if(DEFINED BOARD_WAVESHARE_2_06_APP_MAIN)
  list(APPEND waveshare_watch_src_sources "${BOARD_WAVESHARE_2_06_APP_MAIN}")
endif()

idf_component_register(
    SRCS ${waveshare_watch_src_sources}
    INCLUDE_DIRS "."
    REQUIRES
        esp_lcd
        esp_psram
        esp_adc
        fatfs
        sdmmc
        driver
        esp_driver_i2c
        esp_driver_gpio
)
