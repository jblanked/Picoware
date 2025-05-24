#pragma once
#include "../../internal/gui/draw.hpp"
#include "../../internal/gui/list.hpp"

namespace Picoware
{
    class Menu
    {
    public:
        Menu(
            Draw *draw,
            const char *title,
            uint16_t y,
            uint16_t height,
            uint16_t textColor = TFT_BLACK,
            uint16_t backgroundColor = TFT_WHITE,
            uint16_t selectedColor = TFT_BLUE,
            uint16_t borderColor = TFT_BLACK,
            uint16_t borderWidth = 2);
        ~Menu();
        //
        void clear();
        void draw();
        //
        void addItem(const char *item) { list->addItem(item); }
        void removeItem(uint16_t index) { list->removeItem(index); }
        //
        const char *getCurrentItem() const { return list->getCurrentItem(); }
        const char *getItem(uint16_t index) const { return list->getItem(index); }
        uint16_t getItemCount() const { return list->getItemCount(); }
        uint16_t getListHeight() const { return list->getListHeight(); }
        uint16_t getSelectedIndex() const { return list->getSelectedIndex(); }
        uint16_t getFirstVisibleIndex() const { return list->getFirstVisibleIndex(); }
        uint16_t getVisibleItemCount() const { return list->getVisibleItemCount(); }
        //
        void setSelected(uint16_t index);
        void scrollUp();
        void scrollDown();

    private:
        void drawTitle();
        //
        Draw *display;   // Pointer to the display
        List *list;      // Pointer to the list
        Vector position; // Position of the list
        Vector size;     // Size of the list
        //
        uint16_t textColor;       // Text color of the menu
        uint16_t backgroundColor; // Background color of the menu
        //
        const char *title; // Title of the menu
    };
}