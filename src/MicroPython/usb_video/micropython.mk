USB_VIDEO_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(USB_VIDEO_MOD_DIR)/usb_video_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(USB_VIDEO_MOD_DIR)
