VT_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(VT_MOD_DIR)/vt_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(VT_MOD_DIR)
