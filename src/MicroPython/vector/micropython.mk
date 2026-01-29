VECTOR_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(VECTOR_MOD_DIR)/vector_mp.c

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(VECTOR_MOD_DIR)
