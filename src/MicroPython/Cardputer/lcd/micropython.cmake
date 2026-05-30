# Add the LCD C module for Cardputer.

add_library(usermod_lcd INTERFACE)

target_sources(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
)

target_include_directories(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
    ${CMAKE_CURRENT_LIST_DIR}/../../lcd
)

set(_picoware_idf_path "")
if(DEFINED IDF_PATH)
    set(_picoware_idf_path "${IDF_PATH}")
elseif(DEFINED ENV{IDF_PATH})
    set(_picoware_idf_path "$ENV{IDF_PATH}")
endif()

if(_picoware_idf_path)
    target_include_directories(usermod_lcd INTERFACE
        ${_picoware_idf_path}/components/esp_lcd/include
        ${_picoware_idf_path}/components/esp_lcd/interface
    )
endif()

target_compile_definitions(usermod_lcd INTERFACE
    CARDPUTER
)

target_link_libraries(usermod INTERFACE usermod_lcd)
