PICOWARE_MICROPYTHON_DIR := $(USERMOD_DIR)/../../..
DESKTOP_GHOULS_MOD_DIR := $(USERMOD_DIR)
JSMN_DIR := $(PICOWARE_MICROPYTHON_DIR)/jsmn

# Include the shared module with its own source directory, then restore the port.
USERMOD_DIR := $(PICOWARE_MICROPYTHON_DIR)/ghouls
include $(USERMOD_DIR)/micropython.mk
USERMOD_DIR := $(DESKTOP_GHOULS_MOD_DIR)

# Replace the shared binding with the Desktop adapter; keep the shared game.
SRC_USERMOD_CXX := $(filter-out $(GHOULS_MOD_DIR)/ghouls_mp.cpp,$(SRC_USERMOD_CXX))
SRC_USERMOD_CXX += $(DESKTOP_GHOULS_MOD_DIR)/binding.cpp
SRC_USERMOD += $(DESKTOP_GHOULS_MOD_DIR)/bridge.c
SRC_USERMOD += $(JSMN_DIR)/jsmn.c
SRC_USERMOD += $(JSMN_DIR)/jsmn_h.c

CXXFLAGS_USERMOD += -I$(DESKTOP_GHOULS_MOD_DIR)

# Only game translation units need the Desktop configuration adapter.
DESKTOP_GHOULS_SOURCES := $(filter $(GHOULS_MOD_DIR)/Ghouls/src/%.cpp,$(SRC_USERMOD_LIB_CXX))
DESKTOP_GHOULS_OBJECTS := $(addprefix $(BUILD)/,$(patsubst $(USER_C_MODULES)/%.cpp,%.o,$(DESKTOP_GHOULS_SOURCES)))
$(DESKTOP_GHOULS_OBJECTS): CXXFLAGS += -include $(DESKTOP_GHOULS_MOD_DIR)/compat.hpp
