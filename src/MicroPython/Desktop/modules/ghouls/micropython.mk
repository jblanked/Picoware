PICOWARE_MICROPYTHON_DIR := $(USERMOD_DIR)/../../..
GHOULS_DIR := $(PICOWARE_MICROPYTHON_DIR)/ghouls
GHOULS_MOD_DIR := $(USERMOD_DIR)
JSMN_DIR := $(PICOWARE_MICROPYTHON_DIR)/jsmn
GHOULS_SOURCES := $(wildcard $(GHOULS_DIR)/Ghouls/src/*.cpp)

# Use the firmware game and the engine already linked by the Desktop port.
SRC_USERMOD_CXX += $(GHOULS_MOD_DIR)/binding.cpp
SRC_USERMOD_LIB_CXX += $(GHOULS_SOURCES)
SRC_USERMOD += $(GHOULS_MOD_DIR)/bridge.c
SRC_USERMOD += $(JSMN_DIR)/jsmn.c
SRC_USERMOD += $(JSMN_DIR)/jsmn_h.c
CXXFLAGS_USERMOD += -I$(GHOULS_DIR)
CXXFLAGS_USERMOD += -I$(GHOULS_DIR)/Ghouls/src
CXXFLAGS_USERMOD += -I$(GHOULS_DIR)/Ghouls/src/pico-game-engine
CXXFLAGS_USERMOD += -I$(GHOULS_MOD_DIR)

# Only game translation units need the Desktop configuration adapter.
GHOULS_OBJECTS := $(addprefix $(BUILD)/,$(patsubst $(USER_C_MODULES)/%.cpp,%.o,$(GHOULS_SOURCES)))
$(GHOULS_OBJECTS): CXXFLAGS += -include $(GHOULS_MOD_DIR)/compat.hpp
