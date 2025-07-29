#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/system/pico-calc/sd.hpp"
#include <vector>

using namespace Picoware;

static std::unique_ptr<Menu> fileBrowserMenu = nullptr;
static std::unique_ptr<PicoCalcSD> sdCard = nullptr;
static std::vector<String> directoryStack;
static std::vector<String> directoryContents;
static String currentDirectory = "/";

static void loadDirectoryContents(ViewManager *viewManager)
{
    fileBrowserMenu->clear();
    directoryContents.clear();

    int index = 0;
    while (true)
    {
        File entry = sdCard->getFileOrDirectoryAtIndex(currentDirectory.c_str(), index);

        if (!entry)
        {
            // No more files/directories
            break;
        }

        String itemName = entry.name();

        if (entry.isDirectory())
        {
            itemName += "/";
        }

        directoryContents.push_back(itemName);
        fileBrowserMenu->addItem(directoryContents.back().c_str());
        entry.close();
        index++;
    }

    // If no files found, show empty message
    if (index == 0)
    {
        directoryContents.push_back("(Empty directory)");
        fileBrowserMenu->addItem(directoryContents.back().c_str());
    }

    fileBrowserMenu->setSelected(0);
    fileBrowserMenu->draw();
}

static bool fileBrowserStart(ViewManager *viewManager)
{
    fileBrowserMenu = std::make_unique<Menu>(
        viewManager->getDraw(),            // draw instance
        "File Browser",                    // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    sdCard = std::make_unique<PicoCalcSD>();

    // Initialize directory stack and current directory
    directoryStack.clear();
    directoryContents.clear();
    currentDirectory = "/";

    // Load root directory contents
    loadDirectoryContents(viewManager);

    return true;
}

static void fileBrowserRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();

    switch (input)
    {
    case BUTTON_UP:
        fileBrowserMenu->scrollUp();
        fileBrowserMenu->draw();
        inputManager->reset(true);
        break;

    case BUTTON_DOWN:
        fileBrowserMenu->scrollDown();
        fileBrowserMenu->draw();
        inputManager->reset(true);
        break;

    case BUTTON_LEFT:
    case BUTTON_BACK:
        // Navigate back to previous directory or exit
        if (!directoryStack.empty())
        {
            // Pop the last directory from stack
            currentDirectory = directoryStack.back();
            directoryStack.pop_back();

            // Update menu title to show current path
            String title = "File Browser: " + currentDirectory;
            fileBrowserMenu->setTitle(title.c_str());

            // Reload directory contents
            loadDirectoryContents(viewManager);
        }
        else
        {
            // No more directories in stack, exit the app
            viewManager->back();
        }
        inputManager->reset(true);
        break;

    case BUTTON_CENTER:
    case BUTTON_RIGHT:
    {
        const char *currentItem = fileBrowserMenu->getCurrentItem();
        auto selectedIndex = fileBrowserMenu->getSelectedIndex();

        // Skip if empty directory message
        if (strcmp(currentItem, "(Empty directory)") == 0)
        {
            break;
        }

        // Get the actual file/directory entry
        File selectedEntry = sdCard->getFileOrDirectoryAtIndex(currentDirectory.c_str(), selectedIndex);

        if (selectedEntry)
        {
            if (selectedEntry.isDirectory())
            {
                // It's a directory - navigate into it
                directoryStack.push_back(currentDirectory); // Save current directory to stack

                // Build new directory path
                String newPath = currentDirectory;
                if (newPath != "/")
                {
                    newPath += "/";
                }
                newPath += selectedEntry.name();
                currentDirectory = newPath;

                // Update menu title to show current path
                String title = "File Browser: " + currentDirectory;
                fileBrowserMenu->setTitle(title.c_str());

                // Load new directory contents
                loadDirectoryContents(viewManager);
            }
            else
            {
                // later I'll add file viewing/editing functionality
            }
            selectedEntry.close();
        }
        inputManager->reset(true);
        break;
    }

    default:
        break;
    }
}

static void fileBrowserStop(ViewManager *viewManager)
{
    fileBrowserMenu.reset();
    sdCard.reset();
    directoryStack.clear();
    directoryContents.clear();
    currentDirectory = "/";
}

static const PROGMEM View fileBrowserView = View("File Browser", fileBrowserRun, fileBrowserStart, fileBrowserStop);