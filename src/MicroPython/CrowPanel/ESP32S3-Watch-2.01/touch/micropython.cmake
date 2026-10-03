add_library(usermod_crowpanel_watch_touch INTERFACE)

target_sources(usermod_crowpanel_watch_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
)

target_include_directories(usermod_crowpanel_watch_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

set(_watch_idf_path "")
if(DEFINED IDF_PATH)
  set(_watch_idf_path "${IDF_PATH}")
elseif(DEFINED ENV{IDF_PATH})
  set(_watch_idf_path "$ENV{IDF_PATH}")
endif()

if(_watch_idf_path)
  target_include_directories(usermod_crowpanel_watch_touch INTERFACE
      ${_watch_idf_path}/components/esp_driver_gpio/include
      ${_watch_idf_path}/components/esp_driver_i2c/include
  )
endif()

target_link_libraries(usermod_crowpanel_watch_touch INTERFACE
    idf::esp_driver_gpio
    idf::esp_driver_i2c
    idf::freertos
)

target_link_libraries(usermod INTERFACE usermod_crowpanel_watch_touch)
