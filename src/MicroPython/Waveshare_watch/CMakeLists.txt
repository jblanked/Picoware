set(waveshare_watch_src_sources
    "i2c/i2c_bus.c"
    "lcd/lcd.c"
    "keyboard/keyboard.c"
    "audio/audio.c"
    "sd/sdcard.c"
    "sd/storage.c"
    "imu/imu.c"
    "battery/battery.c"
    "ir/ir.c"
)

if(DEFINED BOARD_WAVESHARE_AMOLED_2_06_ESP32_S3_APP_MAIN)
    list(APPEND waveshare_watch_src_sources "${BOARD_WAVESHARE_AMOLED_2_06_ESP32_S3_APP_MAIN}")
endif()

idf_component_register(
    SRCS ${waveshare_watch_src_sources}
    INCLUDE_DIRS "."
    REQUIRES
        esp_lcd
        esp_adc
        fatfs
        sdmmc
        driver
)
