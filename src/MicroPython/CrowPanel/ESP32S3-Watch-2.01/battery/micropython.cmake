add_library(usermod_crowpanel_watch_battery INTERFACE)

target_sources(usermod_crowpanel_watch_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_crowpanel_watch_battery INTERFACE
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
  target_include_directories(usermod_crowpanel_watch_battery INTERFACE
      ${_watch_idf_path}/components/esp_adc/include
  )
endif()

target_link_libraries(usermod_crowpanel_watch_battery INTERFACE
    idf::esp_adc
    idf::freertos
)

target_link_libraries(usermod INTERFACE usermod_crowpanel_watch_battery)
