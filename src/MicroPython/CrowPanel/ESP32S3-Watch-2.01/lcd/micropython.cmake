add_library(usermod_crowpanel_watch_lcd INTERFACE)

target_sources(usermod_crowpanel_watch_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/gc9309.c
    ${CMAKE_CURRENT_LIST_DIR}/../../../Waveshare/ESP32S3-Touch-LCD-2.06/lcd/lcd.c
)

target_include_directories(usermod_crowpanel_watch_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
    ${CMAKE_CURRENT_LIST_DIR}/../../../Waveshare/ESP32S3-Touch-LCD-2.06
    ${CMAKE_CURRENT_LIST_DIR}/../../../Waveshare/ESP32S3-Touch-LCD-2.06/lcd
)

set(_watch_idf_path "")
if(DEFINED IDF_PATH)
  set(_watch_idf_path "${IDF_PATH}")
elseif(DEFINED ENV{IDF_PATH})
  set(_watch_idf_path "$ENV{IDF_PATH}")
endif()

if(_watch_idf_path)
  target_include_directories(usermod_crowpanel_watch_lcd INTERFACE
      ${_watch_idf_path}/components/esp_driver_gpio/include
      ${_watch_idf_path}/components/esp_driver_spi/include
      ${_watch_idf_path}/components/esp_lcd/include
      ${_watch_idf_path}/components/esp_lcd/interface
  )
endif()

target_link_libraries(usermod_crowpanel_watch_lcd INTERFACE
    idf::esp_lcd
    idf::esp_driver_gpio
    idf::esp_driver_ledc
    idf::esp_driver_spi
    idf::esp_hw_support
)

target_link_libraries(usermod INTERFACE usermod_crowpanel_watch_lcd)
