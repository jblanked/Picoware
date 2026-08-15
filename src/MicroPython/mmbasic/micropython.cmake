# Add the mmbasic C module

add_library(usermod_mmbasic INTERFACE)

target_sources(usermod_mmbasic INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mmbasic_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_builtins.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_console.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_gfx.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_interp.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_lexer.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_nodes.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_num.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_parser.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_rnd.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_runtime.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mbs_util.c
)

target_include_directories(usermod_mmbasic INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_mmbasic)
