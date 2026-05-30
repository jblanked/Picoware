# Add the jsmn C module

add_library(usermod_jsmn INTERFACE)

target_sources(usermod_jsmn INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/jsmn_h.c
    ${CMAKE_CURRENT_LIST_DIR}/jsmn_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/jsmn.c
)

target_include_directories(usermod_jsmn INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_jsmn)
