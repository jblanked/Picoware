#include "../../../internal/boards.hpp"
#include "../../../internal/gui/draw.hpp"
#include "../../../internal/gui/loading.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
using namespace Picoware;
static Loading *loading = nullptr;

static bool loadingStart(ViewManager *viewManager)
{
    loading = new Loading(viewManager->getDraw(), viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    loading->setText("Loading...");
    return true;
}

static void loadingRun(ViewManager *viewManager)
{
    loading->animate(); // Animate the loading spinner
    delay(10);          // Delay for a short period
}

static void loadingStop(ViewManager *viewManager)
{
    if (loading != nullptr)
    {
        loading->stop(); // Stop the loading spinner
        delete loading;
        loading = nullptr;
    }
}

const PROGMEM View loadingView = View("Loading", loadingRun, loadingStart, loadingStop);