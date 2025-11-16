WAVESHARE_BATTERY_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(WAVESHARE_BATTERY_MOD_DIR)/waveshare_battery.c
SRC_USERMOD += $(WAVESHARE_BATTERY_MOD_DIR)/battery.c
# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(WAVESHARE_BATTERY_MOD_DIR)