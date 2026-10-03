# Add the usb_video C module
add_library(usb_video_module INTERFACE)

target_sources(usb_video_module INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/usb_video_mp.c
)

target_include_directories(usb_video_module INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${MICROPY_DIR}/shared/tinyusb
)

target_link_libraries(usermod INTERFACE usb_video_module)

if(DEFINED PICO_RP2350 OR DEFINED PICO_RP2040)
    target_link_libraries(usb_video_module INTERFACE tinyusb_common)
endif()
