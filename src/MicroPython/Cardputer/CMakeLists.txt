set(cardputer_src_sources
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

if(DEFINED CARDPUTER_APP_MAIN)
    list(APPEND cardputer_src_sources "${CARDPUTER_APP_MAIN}")
endif()

idf_component_register(
    SRCS ${cardputer_src_sources}
    INCLUDE_DIRS "."
    REQUIRES
        esp_lcd
        esp_adc
        fatfs
        sdmmc
        driver
)
