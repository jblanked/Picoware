GHOULS_MOD_DIR := $(USERMOD_DIR)

# Add the MicroPython binding to the QSTR/module build.
SRC_USERMOD_CXX += $(GHOULS_MOD_DIR)/ghouls_mp.cpp

# Add the shared game sources as library code.
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/animation.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/dynamic_map.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/enemy.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/game.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/ground.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/level.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/loading.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/map.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/player.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/projectile.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/sky.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/sound.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/time.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_MOD_DIR)/Ghouls/src/weapon.cpp

# Add the module folders to the include paths.
CXXFLAGS_USERMOD += -I$(GHOULS_MOD_DIR)
CXXFLAGS_USERMOD += -I$(GHOULS_MOD_DIR)/Ghouls/src
CXXFLAGS_USERMOD += -I$(GHOULS_MOD_DIR)/Ghouls/src/pico-game-engine
CXXFLAGS_USERMOD += -I$(GHOULS_MOD_DIR)/Ghouls/src/pico-game-engine/engine

# The including port supplies the engine and platform services, including jsmn.
