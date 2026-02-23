# Add the vt C module

add_library(usermod_vt INTERFACE)

target_sources(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/vt_mp.c
)

target_include_directories(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_vt)
