# Add the gpio buttons module.

add_library(usermod_gpio_buttons INTERFACE)

target_sources(usermod_gpio_buttons INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/buttons.c
    ${CMAKE_CURRENT_LIST_DIR}/buttons_mp.c
)

target_include_directories(usermod_gpio_buttons INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_gpio_buttons)
