FLIPPER_ROOT := $(USERMOD_DIR)
SHARED := $(FLIPPER_ROOT)/..

include $(FLIPPER_ROOT)/lcd/micropython.mk
include $(FLIPPER_ROOT)/input/micropython.mk
include $(FLIPPER_ROOT)/battery/micropython.mk
include $(FLIPPER_ROOT)/sd/micropython.mk

SRC_USERMOD += $(SHARED)/auto_complete/auto_complete_mp.c
SRC_USERMOD += $(SHARED)/auto_complete/auto_complete.c
SRC_USERMOD += $(SHARED)/lcd/lcd_mp.c
SRC_USERMOD += $(SHARED)/font/font_mp.c
SRC_USERMOD += $(SHARED)/font/font8.c
SRC_USERMOD += $(SHARED)/font/font12.c
SRC_USERMOD += $(SHARED)/font/font16.c
SRC_USERMOD += $(SHARED)/font/font20.c
SRC_USERMOD += $(SHARED)/font/font24.c
SRC_USERMOD += $(SHARED)/log/log_mp.c
SRC_USERMOD += $(SHARED)/textbox/textbox_mp.c
SRC_USERMOD += $(SHARED)/vector/vector_mp.c
SRC_USERMOD += $(SHARED)/vt/vt_mp.c
SRC_USERMOD += $(SHARED)/response/response_mp.c
SRC_USERMOD += $(SHARED)/picoware_boards/picoware_boards.c
SRC_USERMOD += $(SHARED)/usb_video/usb_video_mp.c

CFLAGS_USERMOD += -I$(SHARED)/auto_complete
CFLAGS_USERMOD += -I$(SHARED)/lcd
CFLAGS_USERMOD += -I$(SHARED)/font
CFLAGS_USERMOD += -I$(SHARED)/log
CFLAGS_USERMOD += -I$(SHARED)/vector
CFLAGS_USERMOD += -I$(SHARED)/vt
CFLAGS_USERMOD += -I$(SHARED)/response
CFLAGS_USERMOD += -I$(SHARED)/picoware_boards
CFLAGS_USERMOD += -I$(SHARED)/sd
CFLAGS_USERMOD += -I$(SHARED)/textbox
CFLAGS_USERMOD += -I$(SHARED)/usb_video
