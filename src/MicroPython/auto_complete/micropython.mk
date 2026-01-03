AUTO_COMPLETE_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(AUTO_COMPLETE_MOD_DIR)/auto_complete.c
SRC_USERMOD += $(AUTO_COMPLETE_MOD_DIR)/auto_complete_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(AUTO_COMPLETE_MOD_DIR)
