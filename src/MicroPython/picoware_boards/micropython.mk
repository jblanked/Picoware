PICOWARE_BOARDS_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_BOARDS_MOD_DIR)/picoware_boards.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_BOARDS_MOD_DIR)
