# Include picoware_lvgl module
add_library(usermod_picoware_lvgl INTERFACE)

target_sources(usermod_picoware_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_alert.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_choice.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_list.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_loading.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_textbox.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl_toggle.c
)

target_include_directories(usermod_picoware_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/lvgl/
    ${CMAKE_CURRENT_LIST_DIR}/lvgl/src
)

# Add LVGL library as subdirectory
add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/lvgl)

target_link_libraries(usermod_picoware_lvgl INTERFACE lvgl_interface)

target_link_libraries(usermod INTERFACE usermod_picoware_lvgl)