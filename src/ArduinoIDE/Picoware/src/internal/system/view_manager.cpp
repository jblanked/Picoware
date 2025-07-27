#include "../../internal/system/buttons.hpp"
#include "../../internal/system/view_manager.hpp"
namespace Picoware
{
    ViewManager::ViewManager(const Board board, uint16_t foregroundColor, uint16_t backgroundColor)
        : picoBoard(board), currentView(nullptr), viewCount(0),
          foregroundColor(foregroundColor), backgroundColor(backgroundColor), selectedColor(TFT_BLUE),
          stackDepth(0),
          led(), storage(), wifi(),
          delayTicks(0), delayElapsed(0)

    {
        this->storage.begin(); // for LittleFS
        this->draw = new Draw(board, true, true);
        this->inputManager = new InputManager(board);
        this->keyboard = new Keyboard(this->draw, this->inputManager, foregroundColor, backgroundColor, TFT_BLUE);
        this->keyboard->setSaveCallback([this](const String &response)
                                        { this->keyboard->setResponse(response); this->back(); });
        for (uint8_t i = 0; i < MAX_VIEWS; i++)
        {
            this->views[i] = nullptr;
        }
        for (uint8_t i = 0; i < MAX_STACK_SIZE; i++)
        {
            this->viewStack[i] = nullptr;
        }
        // slow down the VGM board by 20 ticks
        this->delayTicks = board.boardType == BOARD_TYPE_VGM ? 20 : 0;
        this->clear();
    }

    ViewManager::~ViewManager()
    {
        for (uint8_t i = 0; i < MAX_VIEWS; i++)
        {
            if (this->views[i] != nullptr)
            {
                delete this->views[i];
            }
        }
        delete this->draw;
        delete this->inputManager;
        delete this->keyboard;
    }

    bool ViewManager::add(const View *view)
    {
        if (viewCount >= MAX_VIEWS)
        {
            return false;
        }
        this->views[viewCount] = view;
        this->viewCount++;
        return true;
    }

    void ViewManager::back(bool removeCurrentView)
    {
        if (this->stackDepth > 0)
        {
            const View *viewToRemove = nullptr;

            // Mark current view for removal if requested
            if (this->currentView != nullptr && removeCurrentView)
            {
                viewToRemove = this->currentView;
            }

            // Stop current view
            if (this->currentView != nullptr)
            {
                this->currentView->stop(this);
                this->clear();
            }

            // Pop from stack and set as current view
            this->stackDepth--;
            this->currentView = this->viewStack[this->stackDepth];
            this->viewStack[this->stackDepth] = nullptr;

            // Start the previous view
            if (this->currentView != nullptr)
            {
                if (!this->currentView->start(this))
                {
                    // If the previous view fails to start, try going back again
                    // Don't remove views in recursive calls to avoid complications
                    this->back(false);
                    return;
                }
            }

            // remove the view if requested
            if (viewToRemove != nullptr)
            {
                // Find and remove the view from the views array
                for (uint8_t i = 0; i < this->viewCount; i++)
                {
                    if (this->views[i] == viewToRemove)
                    {
                        // Remove any remaining instances from the stack
                        for (uint8_t j = 0; j < this->stackDepth; j++)
                        {
                            if (this->viewStack[j] == viewToRemove)
                            {
                                // Shift remaining stack elements down
                                for (uint8_t k = j; k < this->stackDepth - 1; k++)
                                {
                                    this->viewStack[k] = this->viewStack[k + 1];
                                }
                                this->stackDepth--;
                                this->viewStack[this->stackDepth] = nullptr;
                                j--; // Check this index again after shifting
                            }
                        }

                        // Remove from views array (but don't delete the view object)
                        for (uint8_t j = i; j < this->viewCount - 1; j++)
                        {
                            this->views[j] = this->views[j + 1];
                        }
                        this->views[this->viewCount - 1] = nullptr;
                        this->viewCount--;
                        break;
                    }
                }
            }
        }
    }

    void ViewManager::clear()
    {
        this->draw->fillScreen(this->backgroundColor);
        this->draw->swap();
    }

    const View *ViewManager::getView(const char *viewName) const noexcept
    {

        for (uint8_t i = 0; i < this->viewCount; i++)
        {

            if (this->views[i] != nullptr)
            {
                if (strcmp(this->views[i]->name, viewName) == 0)
                {
                    return this->views[i];
                }
            }
            else
            {
                Serial.print("ViewManager: View '");
                Serial.print(viewName);
                Serial.print("' found in views array but is NULL. ");
            }
        }
        return nullptr;
    }

    void ViewManager::remove(const char *viewName)
    {
        for (uint8_t i = 0; i < this->viewCount; i++)
        {
            if (strcmp(this->views[i]->name, viewName) == 0)
            {
                // Check if this view is in the stack and remove all instances
                for (uint8_t j = 0; j < this->stackDepth; j++)
                {
                    if (this->viewStack[j] == this->views[i])
                    {
                        // Shift remaining stack elements down
                        for (uint8_t k = j; k < this->stackDepth - 1; k++)
                        {
                            this->viewStack[k] = this->viewStack[k + 1];
                        }
                        this->stackDepth--;
                        this->viewStack[this->stackDepth] = nullptr;
                        j--; // Check this index again after shifting
                    }
                }

                // If this is the current view, clear it
                if (this->currentView == this->views[i])
                {
                    this->currentView->stop(this);
                    this->currentView = nullptr;
                    this->clear();
                }

                delete this->views[i];
                for (uint8_t j = i; j < this->viewCount - 1; j++)
                {
                    this->views[j] = this->views[j + 1];
                }
                this->viewCount--;
                break;
            }
        }
    }

    void ViewManager::run()
    {
        if (this->inputManager != nullptr)
        {
            if (this->inputManager->getInput() == BUTTON_BACK)
            {
                this->inputManager->reset();
                this->back();
            }
            this->inputManager->run();
        }
        if (delayTicks > 0)
        {
            if (this->delayElapsed < delayTicks)
            {
                this->delayElapsed += delayTicks;
                return; // Skip this run cycle if delay not met
            }
            this->delayElapsed = 0; // Reset delay elapsed after running
        }
        if (this->currentView != nullptr)
        {
            this->currentView->run(this);
        }
    }

    void ViewManager::set(const char *viewName)
    {
        if (this->currentView != nullptr)
        {
            this->currentView->stop(this);
            this->clear();
        }
        this->currentView = getView(viewName);
        if (this->currentView != nullptr)
        {
            if (!this->currentView->start(this))
            {
                this->back();
            }
        }
        // Clear the stack when explicitly setting a view
        this->clearStack();
    }

    void ViewManager::switchTo(const char *viewName, bool clearStack, bool pushView)
    {
        auto view = getView(viewName);
        if (view == nullptr)
        {
            Serial.printf("ViewManager: View '%s' not found or is NULL.\n", viewName);
            return;
        }

        // Push current view to stack before switching
        if (this->currentView != nullptr)
        {
            if (clearStack)
            {
                this->clearStack();
            }
            if (pushView)
            {
                this->_pushView(this->currentView);
            }
            this->currentView->stop(this);
            this->clear();
        }

        this->currentView = view;
        if (!this->currentView->start(this))
        {
            this->back();
        }
    }

    void ViewManager::_pushView(const View *view)
    {
        if (this->stackDepth < MAX_STACK_SIZE && view != nullptr)
        {
            this->viewStack[this->stackDepth] = view;
            this->stackDepth++;
        }
    }

    void ViewManager::pushView(const char *viewName)
    {
        auto view = getView(viewName);
        if (view != nullptr)
        {
            this->_pushView(view);
        }
    }

    void ViewManager::clearStack()
    {
        for (uint8_t i = 0; i < this->stackDepth; i++)
        {
            this->viewStack[i] = nullptr;
        }
        this->stackDepth = 0;
    }

}