TOUCH_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(TOUCH_MOD_DIR)/touch_mp.c
SRC_USERMOD += $(TOUCH_MOD_DIR)/touch.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(TOUCH_MOD_DIR)
