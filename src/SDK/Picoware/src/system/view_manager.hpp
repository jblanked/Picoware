#pragma once
#include "../gui/draw.hpp"
#include "../system/colors.hpp"
#include "../system/led.hpp"
#include "../system/storage.hpp"
#include "../system/input.hpp"
#include "../gui/keyboard.hpp"
#include "../system/view.hpp"
#include "../system/wifi.hpp"
#include <ctime>
#include "pico/stdlib.h"
#define DARK_MODE_LOCATION "/dark_mode.json"

class ViewManager
{
public:
    ViewManager();
    ~ViewManager();
    //
    bool add(const View *view);
    void back(bool removeCurrentView = true);
    void clearStack();
    void pushView(const char *viewName);
    void remove(const char *viewName);
    void run();
    void set(const char *viewName);
    void switchTo(const char *viewName, bool clearStack = false, bool push = true);
    //
    uint16_t getBackgroundColor() const noexcept { return backgroundColor; }
    const View *getCurrentView() const noexcept { return currentView; }
    Draw *getDraw() const noexcept { return draw; }
    uint16_t getForegroundColor() const noexcept { return foregroundColor; }
    Input *getInputManager() const noexcept { return inputManager; }
    Keyboard *getKeyboard() const noexcept { return keyboard; }
    LED getLED() const noexcept { return led; }
    uint16_t getSelectedColor() const noexcept { return selectedColor; }
    Vector getSize() const noexcept { return draw->getSize(); }
    uint8_t getStackDepth() const noexcept { return stackDepth; }
    Storage getStorage() const noexcept { return storage; }
    const View *getView(const char *viewName) const noexcept;
    WiFi &getWiFi() noexcept { return wifi; }
    const char *getTime();

    void setBackgroundColor(uint16_t color) noexcept { backgroundColor = color; }
    void setForegroundColor(uint16_t color) noexcept { foregroundColor = color; }
    void setSelectedColor(uint16_t color) noexcept { selectedColor = color; }

private:
    void clear();
    Draw *draw;
    Input *inputManager;
    Keyboard *keyboard;
    const View *currentView;
    Storage storage;
    uint8_t viewCount;
    static constexpr size_t MAX_VIEWS = 10;
    const View *views[MAX_VIEWS];
    uint16_t backgroundColor;
    uint16_t foregroundColor;
    uint16_t selectedColor;
    int delayTicks;
    int delayElapsed;
    LED led;
    WiFi wifi;

    // View stack for navigation history
    void _pushView(const View *view);
    static constexpr size_t MAX_STACK_SIZE = 10;
    const View *viewStack[MAX_STACK_SIZE];
    uint8_t stackDepth;
};
