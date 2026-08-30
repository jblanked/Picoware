PICOWARE_MICROPYTHON_DIR := $(USERMOD_DIR)/../../..
C_MOD_DIR := $(PICOWARE_MICROPYTHON_DIR)/c

SRC_USERMOD += $(C_MOD_DIR)/c_mp.c
SRC_USERMOD += $(C_MOD_DIR)/lib.c
SRC_USERMOD += $(C_MOD_DIR)/io.c
SRC_USERMOD += $(C_MOD_DIR)/pshell/cc/cc.c
SRC_USERMOD += $(C_MOD_DIR)/pshell/cc/cc_malloc.c
SRC_USERMOD += $(C_MOD_DIR)/pshell/cc/cc_peep.c
SRC_USERMOD += $(C_MOD_DIR)/pshell/cc/cc_printf_desktop.c
SRC_USERMOD += $(C_MOD_DIR)/pshell/disassembler/armdisasm.c

CFLAGS_USERMOD += -I$(C_MOD_DIR)
CFLAGS_USERMOD += -I$(C_MOD_DIR)/pshell/cc
CFLAGS_USERMOD += -I$(C_MOD_DIR)/pshell/disassembler
CFLAGS_USERMOD += -DPSHELL_MICROPYTHON
CFLAGS_USERMOD += -DDESKTOP
