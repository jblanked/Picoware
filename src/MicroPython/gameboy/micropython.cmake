# Include gameboy module
add_library(usermod_gameboy INTERFACE)

target_sources(usermod_gameboy INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/buffer.c
    ${CMAKE_CURRENT_LIST_DIR}/flash.c
    ${CMAKE_CURRENT_LIST_DIR}/gameboy_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src/gb.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src/rom.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src/state.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src/ram_cart.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src/audio.c
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/ext/minigb_apu/minigb_apu.c
)

target_include_directories(usermod_gameboy INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/src
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/ext/minigb_apu
    ${CMAKE_CURRENT_LIST_DIR}/PicoCalc-GameBoy/ext/Walnut-CGB
)

target_link_libraries(usermod INTERFACE usermod_gameboy) 