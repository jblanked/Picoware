DESKTOP_ENGINE_DIR := $(USERMOD_DIR)/../../../engine

SRC_USERMOD_CXX += $(wildcard $(DESKTOP_ENGINE_DIR)/*_mp.cpp)
SRC_USERMOD_CXX += $(wildcard $(DESKTOP_ENGINE_DIR)/pico-game-engine/engine/*.cpp)
CXXFLAGS_USERMOD += -std=c++17 -fno-exceptions -fno-rtti
CXXFLAGS_USERMOD += -I$(DESKTOP_ENGINE_DIR)
CXXFLAGS_USERMOD += -I$(DESKTOP_ENGINE_DIR)/pico-game-engine/engine
CXXFLAGS_USERMOD += -I$(USERMOD_DIR)/../../../picoware_boards
LDFLAGS_USERMOD += -lstdc++
