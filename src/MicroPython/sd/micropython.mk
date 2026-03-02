SD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(SD_MOD_DIR)/fat32.c
SRC_USERMOD += $(SD_MOD_DIR)/sd_mp.c
SRC_USERMOD += $(SD_MOD_DIR)/sdcard.c
SRC_USERMOD += $(SD_MOD_DIR)/vfs_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(SD_MOD_DIR)