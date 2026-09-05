# Add the pshell C module.

add_library(usermod_c INTERFACE)

target_sources(usermod_c INTERFACE
	${CMAKE_CURRENT_LIST_DIR}/c_mp.c
)

target_sources(usermod_c INTERFACE
	${CMAKE_CURRENT_LIST_DIR}/lib.c
	${CMAKE_CURRENT_LIST_DIR}/io.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_malloc.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_peep.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/disassembler/armdisasm.c
)

if(PICOWARE_CARDPUTER)
target_sources(usermod_c INTERFACE
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_printf_desktop.c
)
else()
target_sources(usermod_c INTERFACE
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_printf.S
)
endif()

target_include_directories(usermod_c INTERFACE
	${CMAKE_CURRENT_LIST_DIR}
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc
	${CMAKE_CURRENT_LIST_DIR}/pshell/disassembler
)

target_compile_definitions(usermod_c INTERFACE
	PSHELL_MICROPYTHON
)

target_compile_options(usermod_c INTERFACE
	-Wno-error
	-Wno-error=format
	-Wno-error=return-type
	-Wno-error=parentheses
	-Wno-error=unused-value
	-Wno-error=maybe-uninitialized
)

set_source_files_properties(
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_malloc.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/cc/cc_peep.c
	${CMAKE_CURRENT_LIST_DIR}/pshell/disassembler/armdisasm.c
	PROPERTIES COMPILE_OPTIONS "-Wno-error;-Wno-error=format;-Wno-error=return-type;-Wno-error=parentheses;-Wno-error=unused-value"
)

target_link_libraries(usermod INTERFACE usermod_c)