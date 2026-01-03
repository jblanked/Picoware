# Add the auto_complete C module

add_library(usermod_auto_complete INTERFACE)

target_sources(usermod_auto_complete INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/auto_complete.c
    ${CMAKE_CURRENT_LIST_DIR}/auto_complete_mp.c
)

target_include_directories(usermod_auto_complete INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_auto_complete)
