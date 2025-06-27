#pragma once
#include "../../../internal/gui/textbox.hpp"
#include "../../../internal/system/system.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
using namespace Picoware;
static TextBox *systemBox = nullptr;
static String systemText(Board board)
{
    System systemInfo = System();
    String text;
    text += "System Info\n\n";
    text += "Board: " + String(board.name) + "\n\n";
    text += "Free Heap: " + String(systemInfo.freeHeap()) + " bytes\n";
    text += "Used Heap: " + String(systemInfo.usedHeap()) + " bytes\n";
    text += "Total Heap: " + String(systemInfo.totalHeap()) + " bytes\n\n";
    text += "Free PSRAM: " + String(systemInfo.freeHeapPSRAM()) + " bytes\n";
    text += "Used PSRAM: " + String(systemInfo.usedHeapPSRAM()) + " bytes\n";
    text += "Total PSRAM: " + String(systemInfo.totalHeapPSRAM()) + " bytes\n\n";
    text += "Core temperature: " + String(analogReadTemp()) + "C\n";
    return text;
}
static bool systemInfoStart(ViewManager *viewManager)
{
    if (systemBox != nullptr)
    {
        delete systemBox;
        systemBox = nullptr;
    }
    systemBox = new TextBox(viewManager->getDraw(), 0, viewManager->getBoard().height, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    systemBox->setText(systemText(viewManager->getBoard()).c_str());
    return true;
}
static void systemInfoRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto index = inputManager->getInput();
    switch (index)
    {
    case BUTTON_LEFT:
    case BUTTON_BACK:
    {
        viewManager->back();
        inputManager->reset();
        return;
    }
    default:
        if (index != BUTTON_NONE)
        {
            systemBox->setText(systemText(viewManager->getBoard()).c_str());
            inputManager->reset();
        }
        break;
    }
}
static void systemInfoStop(ViewManager *viewManager)
{
    if (systemBox != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            systemBox->clear();
        delete systemBox;
        systemBox = nullptr;
    }
}

const PROGMEM View systemInfoView = View("System Info", systemInfoRun, systemInfoStart, systemInfoStop);