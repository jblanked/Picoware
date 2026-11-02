# Include audio module
add_library(usermod_audio INTERFACE)

target_sources(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/audio_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/audio.c
)

target_include_directories(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# The RP2 back end uses core 1; the ESP32 back end uses ESP-IDF I2S instead.
if(NOT ESP32)
    target_link_libraries(usermod_audio INTERFACE
        pico_multicore
        pico_sync
    )
endif()

target_link_libraries(usermod INTERFACE usermod_audio) 
