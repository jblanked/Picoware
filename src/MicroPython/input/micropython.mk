INPUT_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(INPUT_MOD_DIR)/input_mp.c
SRC_USERMOD += $(INPUT_MOD_DIR)/input.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(INPUT_MOD_DIR)
