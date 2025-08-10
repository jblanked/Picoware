# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(Picoware C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable. Default name is the project name, version 0.1

add_subdirectory(src/system)
add_subdirectory(src/gui)

add_executable(Picoware Picoware.cpp)
target_link_libraries(Picoware system gui)

pico_set_program_name(Picoware "Picoware")
pico_set_program_version(Picoware "0.1")

# Modify the below lines to enable/disable output over UART/USB
pico_enable_stdio_uart(Picoware 0)
pico_enable_stdio_usb(Picoware 0)

# Add the standard library to the build
target_link_libraries(Picoware
        pico_stdlib
        pico_printf
        pico_float
        pico_status_led
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio
        hardware_clocks
        )

# Add WiFi support if available
if (PICO_CYW43_SUPPORTED)
    target_link_libraries(Picoware pico_cyw43_arch_none)
endif()

# Add the standard include files to the build
target_include_directories(Picoware PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
)

pico_add_extra_outputs(Picoware)

