add_library(usermod_crowpanel_watch_storage INTERFACE)

target_sources(usermod_crowpanel_watch_storage INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../storage.c
)

target_include_directories(usermod_crowpanel_watch_storage INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_crowpanel_watch_storage)
