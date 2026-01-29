# Add the vector C module

add_library(usermod_vector INTERFACE)

target_sources(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/vector_mp.c
)

target_include_directories(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_vector)
