# WebSocket module 
add_library(usermod_websocket INTERFACE)

target_sources(usermod_websocket INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/websocket_mp.c
)

target_include_directories(usermod_websocket INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_websocket)
