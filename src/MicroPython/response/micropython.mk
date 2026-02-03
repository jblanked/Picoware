RESPONSE_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(RESPONSE_MOD_DIR)/response_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(RESPONSE_MOD_DIR)
