DESKTOP_GHOULS_DIR := $(USERMOD_DIR)/../../../ghouls
DESKTOP_GHOULS_PORT := $(USERMOD_DIR)
DESKTOP_GHOULS_SOURCES := $(wildcard $(DESKTOP_GHOULS_DIR)/Ghouls/src/*.cpp)

# Use the firmware game and the engine already linked by the Desktop port.
SRC_USERMOD_CXX += $(DESKTOP_GHOULS_PORT)/binding.cpp
SRC_USERMOD_LIB_CXX += $(DESKTOP_GHOULS_SOURCES)
SRC_USERMOD += $(USERMOD_DIR)/bridge.c
SRC_USERMOD += $(USERMOD_DIR)/../../../jsmn/jsmn.c
SRC_USERMOD += $(USERMOD_DIR)/../../../jsmn/jsmn_h.c
CXXFLAGS_USERMOD += -I$(DESKTOP_GHOULS_DIR)
CXXFLAGS_USERMOD += -I$(DESKTOP_GHOULS_DIR)/Ghouls/src
CXXFLAGS_USERMOD += -I$(DESKTOP_GHOULS_DIR)/Ghouls/src/pico-game-engine
CXXFLAGS_USERMOD += -I$(DESKTOP_GHOULS_PORT)

# Only game translation units need the Desktop configuration adapter.
DESKTOP_GHOULS_OBJECTS := $(addprefix $(BUILD)/,$(patsubst $(USER_C_MODULES)/%.cpp,%.o,$(DESKTOP_GHOULS_SOURCES)))
$(DESKTOP_GHOULS_OBJECTS): CXXFLAGS += -include $(DESKTOP_GHOULS_PORT)/compat.hpp
