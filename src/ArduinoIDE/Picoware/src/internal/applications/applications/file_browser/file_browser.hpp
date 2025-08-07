#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/system/pico-calc/sd.hpp"
#include <vector>

using namespace Picoware;

static std::unique_ptr<Menu> fileBrowserMenu = nullptr;
static std::unique_ptr<TextBox> fileBrowserReaderBox = nullptr;
static std::unique_ptr<PicoCalcSD> sdCard = nullptr;
static std::vector<String> directoryStack;
static std::vector<String> directoryContents;
static String currentDirectory = "/";
static bool isViewingFile = false;
static String currentFilePath = "";
static bool firstLoad = true;

static void loadDirectoryContents(ViewManager *viewManager, bool shouldDraw = true)
{
    if (shouldDraw)
    {
        fileBrowserMenu->clear();
    }
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

    if (shouldDraw)
    {
        fileBrowserMenu->setSelected(0);
        fileBrowserMenu->draw();
    }
}

static void showFileContents(ViewManager *viewManager, const String &filePath)
{
    fileBrowserReaderBox->setText("Loading file... hit BACK if this takes too long");
    String fileContent = sdCard->read(filePath.c_str());

    if (fileContent.length() == 0)
    {
        fileContent = "Error: Could not read file or file is empty.";
    }

    // Update text box with file contents and show file
    fileBrowserReaderBox->setText(fileContent.c_str());
    auto lines = fileBrowserReaderBox->getLinesPerScreen() - 1;
    auto index = lines > fileBrowserReaderBox->getTotalLines() ? 0 : lines;
    fileBrowserReaderBox->setCurrentLine(index);
    isViewingFile = true;
    currentFilePath = filePath;
}

static void hideFileContents(ViewManager *viewManager)
{
    // Clear the text box and show the menu again
    fileBrowserReaderBox->clear();
    fileBrowserMenu->draw();
    isViewingFile = false;
    currentFilePath = "";
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

    fileBrowserReaderBox = std::make_unique<TextBox>(
        viewManager->getDraw(),
        0,
        viewManager->getBoard().height,
        viewManager->getForegroundColor(),
        viewManager->getBackgroundColor());

    sdCard = std::make_unique<PicoCalcSD>();

    // Initialize directory stack and current directory
    directoryStack.clear();
    directoryContents.clear();
    currentDirectory = "/";
    isViewingFile = false;
    currentFilePath = "";

    if (firstLoad)
    {
        // Load root directory contents (hack to ensure root directory is loaded)
        // for some reason, the first call since reboot doesnt set the directory names correctly
        // this only happens on the first load after a reboot
        // so we can just do this once
        firstLoad = false;
        loadDirectoryContents(viewManager, false);
        loadDirectoryContents(viewManager, true);
    }
    else
    {
        loadDirectoryContents(viewManager, true);
    }

    return true;
}

static void fileBrowserRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();

    if (isViewingFile)
    {
        switch (input)
        {
        case BUTTON_UP:
            fileBrowserReaderBox->scrollUp();
            inputManager->reset(true);
            break;

        case BUTTON_DOWN:
            fileBrowserReaderBox->scrollDown();
            inputManager->reset(true);
            break;

        case BUTTON_LEFT:
        case BUTTON_BACK:
        case BUTTON_CENTER:
        case BUTTON_RIGHT:
            hideFileContents(viewManager);
            inputManager->reset(true);
            break;

        default:
            break;
        }
    }
    else
    {
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
                    // It's a file - show its contents
                    String filePath = currentDirectory;
                    if (filePath != "/")
                    {
                        filePath += "/";
                    }
                    filePath += selectedEntry.name();

                    showFileContents(viewManager, filePath);
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
}

static void fileBrowserStop(ViewManager *viewManager)
{
    fileBrowserMenu.reset();
    sdCard.reset();
    directoryStack.clear();
    directoryContents.clear();
    currentDirectory = "/";
    isViewingFile = false;
    currentFilePath = "";
    fileBrowserReaderBox.reset();
}

static const PROGMEM View fileBrowserView = View("File Browser", fileBrowserRun, fileBrowserStart, fileBrowserStop);