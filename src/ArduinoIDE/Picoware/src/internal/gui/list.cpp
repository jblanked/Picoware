#include "../../internal/gui/list.hpp"

namespace Picoware
{
    List::List(
        Draw *draw,
        uint16_t y,
        uint16_t height,
        uint16_t textColor,
        uint16_t backgroundColor,
        uint16_t selectedColor,
        uint16_t borderColor,
        uint16_t borderWidth,
        bool showScrollBar)
        : display(draw),
          textColor(textColor),
          backgroundColor(backgroundColor),
          selectedColor(selectedColor),
          borderColor(borderColor),
          borderWidth(borderWidth),
          selectedIndex(0),
          firstVisibleIndex(0),
          linesPerScreen(0),
          visibleItemCount(0),
          showScrollBar(showScrollBar)
    {
        position = Vector(0, y);
        size = Vector(draw->getSize().x, height);
        display->clear(position, size, backgroundColor);
        scrollBar = new ScrollBar(display, Vector(0, 0), Vector(0, 0), borderColor, backgroundColor);

        // font is 2, textSize is 1
        auto board = display->getBoard();
        if (board.libraryType == LIBRARY_TYPE_TFT)
        {
            linesPerScreen = 20; // height is 240
        }
        else
        {
            linesPerScreen = 26; // height is 320
        }

        // Calculate visible item count based on available height and item height
        visibleItemCount = (size.y - 2 * borderWidth) / ITEM_HEIGHT;

        this->display->swap();
    }

    List::~List()
    {
        // Destructor to clean up resources
        delete scrollBar;
        items.clear();
    }

    void List::clear()
    {
        // Clear the list of items
        items.clear();
        selectedIndex = 0;
        firstVisibleIndex = 0;

        // Clear the display area
        display->clear(position, size, backgroundColor);

        setScrollBarSize();
        setScrollBarPosition();

        display->swap();
    }

    void List::draw(bool swap)
    {
        // Clear the display area
        display->clear(position, size, backgroundColor);

        // Draw only visible items
        uint16_t displayed = 0;
        for (uint16_t i = firstVisibleIndex; i < items.size() && displayed < visibleItemCount; i++)
        {
            drawItem(i, i == selectedIndex);
            displayed++;
        }

        if (showScrollBar)
        {
            // Draw the scrollbar
            setScrollBarSize();
            setScrollBarPosition();
            scrollBar->draw();
        }

        // swap the display buffer
        if (swap)
            display->swap();
    }

    void List::addItem(const char *item)
    {
        // Add an item to the list
        items.push_back(item);

        // Update visibility if necessary
        updateVisibility();
    }

    void List::removeItem(uint16_t index)
    {
        // Remove an item from the list
        if (index < items.size())
        {
            items.erase(items.begin() + index);

            // Adjust selectedIndex if necessary
            if (selectedIndex >= items.size())
                selectedIndex = items.size() > 0 ? items.size() - 1 : 0;

            // Update visibility
            updateVisibility();
        }
    }

    void List::setSelected(uint16_t index)
    {
        // Set the selected item in the list
        if (index < items.size())
        {
            selectedIndex = index;
            updateVisibility();
            draw();
        }
    }

    void List::scrollUp()
    {
        setSelected(selectedIndex > 0 ? selectedIndex - 1 : 0);
    }

    void List::scrollDown()
    {
        setSelected(selectedIndex < items.size() - 1 ? selectedIndex + 1 : items.size() - 1);
    }

    void List::updateVisibility()
    {
        // Make sure the selected item is visible
        if (selectedIndex < firstVisibleIndex)
        {
            // Selected item is above visible area, scroll up
            firstVisibleIndex = selectedIndex;
        }
        else if (selectedIndex >= firstVisibleIndex + visibleItemCount)
        {
            // Selected item is below visible area, scroll down
            firstVisibleIndex = selectedIndex - visibleItemCount + 1;
        }

        setScrollBarSize();
        setScrollBarPosition();
    }

    void List::drawItem(uint16_t index, bool selected)
    {
        // Calculate the position within the visible area
        uint16_t visibleIndex = index - firstVisibleIndex;
        uint16_t y = position.y + borderWidth + visibleIndex * ITEM_HEIGHT;

        // Check if the item is within visible bounds
        if (visibleIndex >= visibleItemCount)
        {
            return;
        }

        // Draw item background
        if (selected)
        {
            display->fillRect(
                Vector(position.x + borderWidth, y),
                Vector(size.x - 2 * borderWidth, ITEM_HEIGHT),
                selectedColor);
        }
        else
        {
            display->fillRect(
                Vector(position.x + borderWidth, y),
                Vector(size.x - 2 * borderWidth, ITEM_HEIGHT),
                backgroundColor);
        }

        // Draw line separator
        if (borderWidth > 0)
        {
            display->drawLine(
                Vector(position.x + borderWidth, y + ITEM_HEIGHT - 1),
                Vector(position.x + size.x - borderWidth - 1, y + ITEM_HEIGHT - 1),
                borderColor);
        }

        // Draw the item text
        display->text(
            Vector(position.x + borderWidth + 5, y + 5),
            items[index],
            textColor);
    }

    void List::setScrollBarSize()
    {
        // Get the total content height and visible view height
        float contentHeight = getListHeight();
        float viewHeight = size.y - 2 * borderWidth;

        // Fixed width for scrollbar
        const float barWidth = 6.0f;

        // Calculate the scrollbar thumb height proportionally
        float barHeight;

        // Always show the scrollbar with a minimum height
        if (items.size() <= visibleItemCount || contentHeight <= viewHeight)
        {
            // Even if scrolling isn't needed, show a full-height scrollbar
            barHeight = viewHeight;
        }
        else
        {
            // Calculate proportional height of the scrollbar thumb
            // Thumb size = (visible portion / total content) * view height
            barHeight = (float)visibleItemCount / items.size() * viewHeight;

            // Enforce minimum scrollbar height for usability
            const float minBarHeight = 12.0f;
            if (barHeight < minBarHeight)
                barHeight = minBarHeight;

            // Make sure it doesn't exceed view height
            if (barHeight > viewHeight)
                barHeight = viewHeight;
        }

        scrollBar->setSize(Vector(barWidth, barHeight));
    }

    void List::setScrollBarPosition()
    {
        Vector barSize = scrollBar->getSize();
        float barHeight = barSize.y;
        float barWidth = barSize.x;

        // Calculate available scrollable area (view height minus scrollbar thumb height)
        float viewHeight = size.y - 2 * borderWidth;
        float scrollableArea = 0;

        // Position scrollbar on the right side of the list
        float barX = position.x + size.x - barWidth - 1;
        float barY = position.y + borderWidth; // Default to top

        // Only calculate scroll position if we need scrolling
        if (items.size() > visibleItemCount)
        {
            scrollableArea = viewHeight - barHeight;

            // Calculate scroll position ratio based on first visible index and total scrollable items
            float scrollRatio = 0.0f;

            // Calculate the current scroll position as a ratio
            // Current position = firstVisibleIndex / (total items - visible items)
            int maxFirstVisible = items.size() - visibleItemCount;
            if (maxFirstVisible > 0)
            {
                scrollRatio = (float)firstVisibleIndex / maxFirstVisible;

                // Clamp between 0 and 1
                if (scrollRatio < 0.0f)
                    scrollRatio = 0.0f;
                if (scrollRatio > 1.0f)
                    scrollRatio = 1.0f;

                // Calculate Y position based on scroll ratio
                barY = position.y + borderWidth + scrollRatio * scrollableArea;
            }
        }

        scrollBar->setPosition(Vector(barX, barY));
    }
}