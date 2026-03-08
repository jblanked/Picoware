# Add the engine C module

add_library(usermod_engine INTERFACE)

target_sources(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/camera_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/engine_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/entity_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/game_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/level_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/sprite3d_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/triangle3d_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/engine/draw.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/entity.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/image.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/level.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/sprite3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/triangle3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/engine/vector.cpp
)

target_include_directories(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_engine)
