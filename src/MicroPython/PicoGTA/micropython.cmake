# Include pico_gta module
add_library(usermod_pico_gta INTERFACE)

target_sources(usermod_pico_gta INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/pico_gta_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/building.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/landscape.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/map.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/pedestrian.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/player.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/road.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/sound.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/time.cpp
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/vehicle.cpp
) 

target_include_directories(usermod_pico_gta INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/pico-game-engine
    ${CMAKE_CURRENT_LIST_DIR}/PicoGTA/src/pico-game-engine/engine
)

target_link_libraries(usermod INTERFACE usermod_pico_gta)

# pico_gta uses pico-game-engine symbols compiled by usermod_engine;
# im linking here to avoid recompiling the same sources
target_link_libraries(usermod_pico_gta INTERFACE usermod_engine)