LCD_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(LCD_MOD_DIR)/lcd_mp.c
SRC_USERMOD += $(LCD_MOD_DIR)/lcd.c
SRC_USERMOD += $(LCD_MOD_DIR)/font8.c
SRC_USERMOD += $(LCD_MOD_DIR)/font12.c
SRC_USERMOD += $(LCD_MOD_DIR)/font16.c
SRC_USERMOD += $(LCD_MOD_DIR)/font20.c
SRC_USERMOD += $(LCD_MOD_DIR)/font24.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(LCD_MOD_DIR)
