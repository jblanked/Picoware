#pragma once
#include <Arduino.h>
#include "../../internal/boards.hpp"
#include "../../internal/gui/draw.hpp"
#include "../../internal/system/colors.hpp"
#include "../../internal/system/led.hpp"
#include "../../internal/system/storage.hpp"
#include "../../internal/system/input_manager.hpp"
#include "../../internal/system/keyboard.hpp"
#include "../../internal/system/view.hpp"
#include "../../internal/system/wifi_utils.hpp"
namespace Picoware
{
    class ViewManager
    {
    public:
        ViewManager(const Board board, uint16_t foregroundColor = TFT_BLACK, uint16_t backgroundColor = TFT_WHITE);
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
        Board getBoard() const noexcept { return picoBoard; }
        const View *getCurrentView() const noexcept { return currentView; }
        Draw *getDraw() const noexcept { return draw; }
        uint16_t getForegroundColor() const noexcept { return foregroundColor; }
        InputManager *getInputManager() const noexcept { return inputManager; }
        Keyboard *getKeyboard() const noexcept { return keyboard; }
        LED getLED() const noexcept { return led; }
        uint16_t getSelectedColor() const noexcept { return selectedColor; }
        Vector getSize() const noexcept { return draw->getSize(); }
        uint8_t getStackDepth() const noexcept { return stackDepth; }
        Storage getStorage() const noexcept { return storage; }
        const View *getView(const char *viewName) const noexcept;
        WiFiUtils getWiFi() const noexcept { return wifi; }
        const char *getTime()
        {
            if (wifi.isConnected())
            {
                struct tm timeinfo;
                if (wifi.setTime(timeinfo, 5000))
                {
                    static char timeBuffer[9]; // Buffer for formatted time string (HH:MM:SS)
                    sprintf(timeBuffer, "%02d:%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
                    return timeBuffer;
                }
            }
            return nullptr;
        }

    private:
        void clear();
        Board picoBoard;
        Draw *draw;
        InputManager *inputManager;
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
        WiFiUtils wifi;

        // View stack for navigation history
        void _pushView(const View *view);
        static constexpr size_t MAX_STACK_SIZE = 10;
        const View *viewStack[MAX_STACK_SIZE];
        uint8_t stackDepth;
    };
}