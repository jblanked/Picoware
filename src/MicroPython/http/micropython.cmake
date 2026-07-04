# HTTP module
add_library(usermod_http INTERFACE)

target_sources(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/http_mp.c
)

target_include_directories(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_http)
