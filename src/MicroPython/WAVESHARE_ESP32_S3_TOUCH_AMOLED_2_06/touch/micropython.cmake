# Add the touch C module

add_library(usermod_touch INTERFACE)

target_sources(usermod_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
)

target_include_directories(usermod_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

set(_picoware_idf_path "")
if(DEFINED IDF_PATH)
  set(_picoware_idf_path "${IDF_PATH}")
elseif(DEFINED ENV{IDF_PATH})
  set(_picoware_idf_path "$ENV{IDF_PATH}")
endif()

if(_picoware_idf_path)
  target_include_directories(usermod_touch INTERFACE
        ${_picoware_idf_path}/components/esp_lcd/include
        ${_picoware_idf_path}/components/esp_lcd/interface
    )
endif()

target_compile_definitions(usermod_lcd INTERFACE
  WAVESHARE_2_06
)

target_link_libraries(usermod INTERFACE usermod_touch)
