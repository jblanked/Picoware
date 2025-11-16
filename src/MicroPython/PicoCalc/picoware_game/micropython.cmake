# Add the picoware_game C module

add_library(usermod_picoware_game INTERFACE)

target_sources(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_game.c
)

target_include_directories(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_picoware_game)
