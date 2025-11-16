PICOWARE_KEYBOARD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_KEYBOARD_MOD_DIR)/picoware_keyboard.c
SRC_USERMOD += $(PICOWARE_KEYBOARD_MOD_DIR)/picoware_southbridge.c
SRC_USERMOD += $(PICOWARE_KEYBOARD_MOD_DIR)/keyboard.c
SRC_USERMOD += $(PICOWARE_KEYBOARD_MOD_DIR)/southbridge.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_KEYBOARD_MOD_DIR)
