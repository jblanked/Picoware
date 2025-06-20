#pragma once
#include "../../internal/gui/draw.hpp"
#include "../../internal/gui/scrollbar.hpp"

namespace Picoware
{
    class List
    {
    public:
        List(
            Draw *draw,
            uint16_t y,
            uint16_t height,
            uint16_t textColor = TFT_BLACK,
            uint16_t backgroundColor = TFT_WHITE,
            uint16_t selectedColor = TFT_BLUE,
            uint16_t borderColor = TFT_BLACK,
            uint16_t borderWidth = 2,
            bool showScrollBar = true);
        ~List();
        //
        void clear();
        void draw(bool swap = true);
        //
        void addItem(const char *item);
        void removeItem(uint16_t index);
        //
        const char *getCurrentItem() const
        {
            return getItem(selectedIndex);
        }
        const char *getItem(uint16_t index) const
        {
            if (index < items.size())
                return items[index];
            return nullptr;
        }
        uint16_t getItemCount() const { return items.size(); }
        uint16_t getListHeight() const { return getItemCount() * ITEM_HEIGHT; }
        uint16_t getSelectedIndex() const { return selectedIndex; }
        uint16_t getFirstVisibleIndex() const { return firstVisibleIndex; }
        uint16_t getVisibleItemCount() const { return visibleItemCount; }
        //
        void setSelected(uint16_t index);
        void scrollUp();
        void scrollDown();

        // Constants
        static const uint16_t ITEM_HEIGHT = 20; // Height of each item in pixels

    private:
        void drawItem(uint16_t index, bool selected);
        void updateVisibility();
        void setScrollBarPosition(); // Helper function to set the scrollbar position
        void setScrollBarSize();     // Helper function to set the scrollbar size
        //
        Draw *display;                   // Pointer to the display
        ScrollBar *scrollBar;            // Pointer to the scrollbar
        Vector position;                 // Position of the list
        Vector size;                     // Size of the list
        uint16_t textColor;              // Text color of the list
        uint16_t backgroundColor;        // Background color of the list
        uint16_t selectedColor;          // Selected item color
        uint16_t borderColor;            // Border color of the list
        uint16_t borderWidth;            // Border width of the list
        uint16_t selectedIndex;          // Index of the currently selected item
        uint16_t firstVisibleIndex;      // Index of the first visible item
        uint16_t visibleItemCount;       // Number of items visible at once
        uint16_t linesPerScreen;         // Number of lines that fit in the list
        bool showScrollBar;              // Whether to show the scrollbar
        std::vector<const char *> items; // List of items in the list
    };
}