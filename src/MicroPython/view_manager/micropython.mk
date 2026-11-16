VIEW_MANAGER_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(VIEW_MANAGER_MOD_DIR)/view_manager_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(VIEW_MANAGER_MOD_DIR)
