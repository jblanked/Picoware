
add_library(usermod_jpegdec INTERFACE)

# Add our source files to the lib
target_sources(usermod_jpegdec INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/jpegdec.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_jpegdec INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_jpegdec)
