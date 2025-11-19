WAVESHARE_SD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(WAVESHARE_SD_MOD_DIR)/waveshare_sd.c
SRC_USERMOD += $(WAVESHARE_SD_MOD_DIR)/sdcard.c
SRC_USERMOD += $(WAVESHARE_SD_MOD_DIR)/fat32.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(WAVESHARE_SD_MOD_DIR)