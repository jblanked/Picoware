# Include audio module
add_library(usermod_audio INTERFACE)

target_sources(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/audio_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/audio.c
)

target_include_directories(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# RP2 uses core 1; ESP32 uses the codec's I2S backend or POOM's LEDC buzzer.
if(PICOWARE_AUDIO_BACKEND STREQUAL "poom")
    target_link_libraries(usermod_audio INTERFACE
        idf::esp_driver_ledc
    )
elseif(PICOWARE_AUDIO_BACKEND STREQUAL "pdm")
    target_link_libraries(usermod_audio INTERFACE
        idf::esp_driver_i2s
    )
elseif(NOT ESP32)
    target_link_libraries(usermod_audio INTERFACE
        pico_multicore
        pico_sync
    )
endif()

target_link_libraries(usermod INTERFACE usermod_audio) 
