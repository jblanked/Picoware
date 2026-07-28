# Add the shared I2C bus helper for Pancake.
# Both the touch controller and the fuel gauge depend on this.

add_library(usermod_pancake_i2c INTERFACE)

target_sources(usermod_pancake_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/i2c_bus.c
)

target_include_directories(usermod_pancake_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_pancake_i2c)
