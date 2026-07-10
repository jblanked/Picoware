# Include ghouls module
add_library(usermod_ghouls INTERFACE)

target_sources(usermod_ghouls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/ghouls_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/animation.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/dynamic_map.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/enemy.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/ground.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/level.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/loading.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/map.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/player.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/projectile.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/sky.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/sound.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/time.cpp
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/weapon.cpp
) 

target_include_directories(usermod_ghouls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/pico-game-engine
    ${CMAKE_CURRENT_LIST_DIR}/Ghouls/src/pico-game-engine/engine
)

target_link_libraries(usermod INTERFACE usermod_ghouls)

# ghouls uses pico-game-engine symbols compiled by usermod_engine;
# im linking here to avoid recompiling the same sources
target_link_libraries(usermod_ghouls INTERFACE usermod_engine)