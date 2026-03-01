# Add the picoware_boards C module

add_library(usermod_picoware_boards INTERFACE)

target_sources(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_boards.c
)

target_include_directories(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_picoware_boards)
