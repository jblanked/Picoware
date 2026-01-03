PICOWARE_PSRAM_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_PSRAM_MOD_DIR)/picoware_psram.c
SRC_USERMOD += $(PICOWARE_PSRAM_MOD_DIR)/psram_qspi.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_PSRAM_MOD_DIR)
