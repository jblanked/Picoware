# HTTP module
add_library(usermod_http INTERFACE)

target_sources(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/http_mp.c
)

target_include_directories(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# When lwIP is available (wireless boards), add altcp sources for HTTP/HTTPS
if(MICROPY_PY_LWIP)
    target_sources(usermod_http INTERFACE
        ${PICO_LWIP_PATH}/src/core/altcp.c
        ${PICO_LWIP_PATH}/src/core/altcp_tcp.c
        ${MICROPY_DIR}/lib/pico-sdk/src/rp2_common/pico_lwip/altcp_tls_mbedtls.c
    )
    target_include_directories(usermod_http INTERFACE
        ${PICO_LWIP_PATH}/src/include
        ${PICO_LWIP_PATH}/src/apps/altcp_tls
    )
    target_compile_definitions(usermod_http INTERFACE
        LWIP_ALTCP=1
        LWIP_ALTCP_TLS=1
        LWIP_ALTCP_TLS_MBEDTLS=1
    )
    # Redirect altcp_alloc/altcp_free (which use uninitialised memp pools)
    # to our __wrap_ versions that use lwIP's general heap instead.
    target_link_options(usermod_http INTERFACE
        -Wl,--wrap=altcp_alloc
        -Wl,--wrap=altcp_free
    )
    set_source_files_properties(
        ${MICROPY_DIR}/lib/pico-sdk/src/rp2_common/pico_lwip/altcp_tls_mbedtls.c
        PROPERTIES COMPILE_DEFINITIONS "MBEDTLS_ALLOW_PRIVATE_ACCESS=1"
    )
endif()

target_link_libraries(usermod INTERFACE usermod_http) 