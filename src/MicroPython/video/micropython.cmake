add_library(usermod_video INTERFACE)

target_sources(usermod_video INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/video_mp.c
)

target_include_directories(usermod_video INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_video)