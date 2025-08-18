#include "../gui/menu.hpp"

Menu::Menu(
    Draw *draw,
    const char *title,
    uint16_t y,
    uint16_t height,
    uint16_t textColor,
    uint16_t backgroundColor,
    uint16_t selectedColor,
    uint16_t borderColor,
    uint16_t borderWidth,
    bool showScrollBar) : title(title)
{
    this->display = draw;
    this->textColor = textColor;
    this->backgroundColor = backgroundColor;
    list = new List(draw, y + 20, height - 20, textColor, backgroundColor, selectedColor, borderColor, borderWidth, showScrollBar);
    this->position = Vector(0, y);
    this->size = Vector(draw->getSize().x, height);
    this->display->clear(position, size, backgroundColor);
    this->display->swapRegion(position, size);
}

Menu::~Menu()
{
    delete list;
}

void Menu::clear()
{
    this->display->clear(position, size, backgroundColor);
    list->clear();
}

void Menu::draw()
{
    // Clear the title area first to prevent artifacts
    Vector titleArea = Vector(display->getSize().x, 20);
    display->clear(position, titleArea, backgroundColor);

    drawTitle();
    list->draw(false); // Don't swap yet

    // Single swap for the entire menu area
    display->swapRegion(position, size);
}

void Menu::drawTitle()
{
    display->text(Vector(2, position.y + 2), title, textColor, 4);
}

void Menu::scrollDown()
{
    list->scrollDown();
}

void Menu::scrollUp()
{
    list->scrollUp();
}

void Menu::setTitle(const char *newTitle)
{
    title = newTitle;
    // Clear the title area and redraw
    Vector titleArea = Vector(display->getSize().x, 20);
    display->clear(position, titleArea, backgroundColor);
    drawTitle();
    display->swapRegion(position, titleArea);
}

void Menu::setSelected(uint16_t index)
{
    drawTitle();
    list->setSelected(index);
}
