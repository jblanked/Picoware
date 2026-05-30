# Add the log C module

add_library(usermod_log INTERFACE)

target_sources(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/log_mp.c
)

target_include_directories(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_log)
