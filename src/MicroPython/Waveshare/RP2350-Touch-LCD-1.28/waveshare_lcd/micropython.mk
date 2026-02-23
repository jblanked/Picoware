WAVESHARE_LCD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(WAVESHARE_LCD_MOD_DIR)/lcd.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(WAVESHARE_LCD_MOD_DIR)
