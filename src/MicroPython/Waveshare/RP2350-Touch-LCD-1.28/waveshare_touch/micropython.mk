WAVESHARE_TOUCH_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(WAVESHARE_TOUCH_MOD_DIR)/waveshare_touch.c
SRC_USERMOD += $(WAVESHARE_TOUCH_MOD_DIR)/touch.c
# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(WAVESHARE_TOUCH_MOD_DIR)