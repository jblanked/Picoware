PICOWARE_LVGL_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(PICOWARE_LVGL_MOD_DIR)/picoware_lvgl.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(PICOWARE_LVGL_MOD_DIR)
