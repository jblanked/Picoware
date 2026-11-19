PICO_GTA_MOD_DIR := $(USERMOD_DIR)

# Add the MicroPython binding to the QSTR/module build.
SRC_USERMOD_CXX += $(PICO_GTA_MOD_DIR)/pico_gta_mp.cpp

# Add the shared game sources as library code.
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/building.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/game.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/landscape.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/map.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/pedestrian.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/player.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/road.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/sound.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/time.cpp
SRC_USERMOD_LIB_CXX += $(PICO_GTA_MOD_DIR)/PicoGTA/src/vehicle.cpp

# Add the module folders to the include paths.
CXXFLAGS_USERMOD += -I$(PICO_GTA_MOD_DIR)
CXXFLAGS_USERMOD += -I$(PICO_GTA_MOD_DIR)/PicoGTA/src
CXXFLAGS_USERMOD += -I$(PICO_GTA_MOD_DIR)/PicoGTA/src/pico-game-engine
CXXFLAGS_USERMOD += -I$(PICO_GTA_MOD_DIR)/PicoGTA/src/pico-game-engine/engine

# The including port supplies the engine and platform services, including jsmn.
