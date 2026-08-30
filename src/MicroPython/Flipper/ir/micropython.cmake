add_library(usermod_flipper_ir INTERFACE)

target_sources(usermod_flipper_ir INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/ir_mp.c
)

target_link_libraries(usermod INTERFACE usermod_flipper_ir)
