PICOWARE_GAME_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_GAME_MOD_DIR)/picoware_game.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_GAME_MOD_DIR)
