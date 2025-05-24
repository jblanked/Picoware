#pragma once
#include "Arduino.h"
#include "../../internal/boards.hpp"
#include "../../internal/system/input.hpp"
namespace Picoware
{
    class InputManager
    {
    public:
        InputManager(const Board board) : input(-1)
        {
            for (int i = 0; i < 5; i++)
            {
                inputs[i] = nullptr;
            }
            if (board.boardType == BOARD_TYPE_VGM)
            {
                isUARTInput = true;
                inputs[0] = new Input(new ButtonUART());
            }
            else if (board.boardType == BOARD_TYPE_JBLANKED)
            {
                isUARTInput = false;
                float debounce = 0.05f;
                inputs[0] = new Input(16, BUTTON_UP, debounce);
                inputs[1] = new Input(17, BUTTON_RIGHT, debounce);
                inputs[2] = new Input(18, BUTTON_DOWN, debounce);
                inputs[3] = new Input(19, BUTTON_LEFT, debounce);
                inputs[4] = new Input(20, BUTTON_CENTER, debounce);
            }
            else
            {
                // pass for now
                isUARTInput = false;
            }
        }

        ~InputManager()
        {
            for (int i = 0; i < 4; i++)
            {
                if (inputs[i] != nullptr)
                {
                    delete inputs[i];
                    inputs[i] = nullptr;
                }
            }
        }

        // Reset the input
        inline void reset(bool shouldDelay = false, int delayMs = 150)
        {
            input = -1;
            for (int i = 0; i < 5; i++)
            {
                if (inputs[i] != nullptr)
                {
                    inputs[i]->reset();
                }
            }
            if (shouldDelay)
            {
                delay(delayMs);
            }
        }

        // Run the input manager and check for input events.
        inline void run()
        {
            if (isUARTInput)
            {
                inputs[0]->run();
                input = inputs[0]->getLastButton();
            }
            else
            {
                // Reset input to -1 at start of each run cycle
                input = -1;
                for (int i = 0; i < 5; i++)
                {
                    if (inputs[i] != nullptr)
                    {
                        inputs[i]->run();
                        // Check if button was just pressed (not held)
                        if (inputs[i]->getLastButton() != -1)
                        {
                            input = inputs[i]->getButtonAssignment();
                            break;
                        }
                    }
                }
            }
        }

        int getInput() const noexcept
        {
            return input;
        }

    private:
        int input;
        bool isUARTInput;
        Input *inputs[5]; // 5 for now until we add the Picocalc buttons
    };
}