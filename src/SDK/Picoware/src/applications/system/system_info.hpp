#pragma once
#include "../../gui/textbox.hpp"
#include "../../system/system.hpp"
#include "../../system/view.hpp"
#include "../../system/view_manager.hpp"

static TextBox *systemBox = nullptr;
static String systemText()
{
    String text;
    text += "System Info\n\n";
    text += "Free Heap: " + std::to_string(System::freeHeap()) + " bytes\n";
    text += "Used Heap: " + std::to_string(System::usedHeap()) + " bytes\n";
    text += "Total Heap: " + std::to_string(System::totalHeap()) + " bytes\n\n";
    text += "Free PSRAM: " + std::to_string(System::freeHeapPSRAM()) + " bytes\n";
    text += "Used PSRAM: " + std::to_string(System::usedHeapPSRAM()) + " bytes\n";
    text += "Total PSRAM: " + std::to_string(System::totalHeapPSRAM()) + " bytes\n";
    return text;
}

static bool systemInfoStart(ViewManager *viewManager)
{
    if (systemBox != nullptr)
    {
        delete systemBox;
        systemBox = nullptr;
    }
    systemBox = new TextBox(viewManager->getDraw(), 0, 320, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    systemBox->setText(systemText().c_str());
    return true;
}
static void systemInfoRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto index = inputManager->getLastButton();
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
            systemBox->setText(systemText().c_str());
            inputManager->reset();
        }
        break;
    }
}
static void systemInfoStop(ViewManager *viewManager)
{
    if (systemBox != nullptr)
    {
        delete systemBox;
        systemBox = nullptr;
    }
}

static const View systemInfoView = View("System Info", systemInfoRun, systemInfoStart, systemInfoStop);