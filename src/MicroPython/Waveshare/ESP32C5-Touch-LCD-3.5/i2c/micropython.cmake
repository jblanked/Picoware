# Add the shared I2C bus helper for the WS C5-3.5.
# Both the touch controller and the fuel gauge depend on this.

add_library(usermod_ws_c5_35_i2c INTERFACE)

target_sources(usermod_ws_c5_35_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/i2c_bus.c
)

target_include_directories(usermod_ws_c5_35_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_ws_c5_35_i2c)
