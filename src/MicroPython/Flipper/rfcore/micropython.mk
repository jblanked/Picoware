SRC_USERMOD += $(USERMOD_DIR)/rfcore/rfcore_stub.c
LDFLAGS_USERMOD += -Wl,--wrap=rfcore_init -Wl,--wrap=rfcore_start_flash_erase -Wl,--wrap=rfcore_end_flash_erase
