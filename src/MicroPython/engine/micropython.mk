ENGINE_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(ENGINE_MOD_DIR)/camera_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/entity_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/game_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/level_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/sprite3d_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/triangle3d_mp.c
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/draw.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/entity.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/game.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/image.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/level.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/sprite3d.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/triangle3d.cpp
SRC_USERMOD += $(ENGINE_MOD_DIR)/engine/vector.cpp

# We can add our module folder to include paths if needed
CFLAGS_USERMOD += -I$(ENGINE_MOD_DIR)
	