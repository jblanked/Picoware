PICOWARE_SD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_SD_MOD_DIR)/picoware_sd.c
SRC_USERMOD += $(PICOWARE_SD_MOD_DIR)/picoware_vfs.c
SRC_USERMOD += $(PICOWARE_SD_MOD_DIR)/sdcard.c
SRC_USERMOD += $(PICOWARE_SD_MOD_DIR)/fat32.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_SD_MOD_DIR)