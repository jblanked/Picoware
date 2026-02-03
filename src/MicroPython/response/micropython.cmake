# Add the response C module

add_library(usermod_response INTERFACE)

target_sources(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/response_mp.c
)

target_include_directories(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_response)
