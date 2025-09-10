# Apps
This details external app creation and structure for the Micropython version of Picoware.

> [!NOTE]
> This is only available in the MicroPython version of Picoware.

## Overview
Picoware supports external applications that can be created by users and developers. These applications can be written in MicroPython and can leverage the Picoware API to interact with the device's hardware and software. 

## Saving Applications
Applications should be saved in the `picoware/apps` directory on your SD Card. Due to limited ram, applications should be kept as small as possible and should be thoroughly tested (using Thonny or another IDE) before being added to the device.

## Application Structure
Each application should be structured in a specific way to ensure compatibility with Picoware. It must contains the following methods:
- `start(view_manager)`: This boolean method is called when the application is launched. It should contain the initialization code for the application. If it returns `False`, the application will not be launched.
- `stop(view_manager)`: This method is called when the application is closed. It should contain the cleanup code for the application.
- `run(view_manager)`: This method is called repeatedly while the application is running. It should contain the main logic of the application.

Note that the `view_manager` parameter is an instance of the `ViewManager` class, which provides methods to manage views and interact with the device's display. Lastly, the `run` method should be **non-blocking** to ensure the application remains responsive and contains a `view_manager.back()` call to allow users to exit the application.

## Example Application
Here is a simple example of an application that displays a message on the screen:
```python
def start(view_manager):
    '''Start the app'''
    from picoware.system.vector import Vector
    from time import sleep

    draw = view_manager.get_draw()
    draw.clear()
    draw.text(Vector(10, 10), "Example App")
    draw.swap()

    sleep(2)  # Brief pause to let user read the header
    return True

def run(view_manager):  
    '''Run the app'''
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )
    input_manager = view_manager.input_manager
    button = input_manager.get_last_button()
    if button == BUTTON_BACK:
        input_manager.reset(True) # reset to avoid multiple back presses
        view_manager.back()

def stop(view_manager):
    '''Stop the app'''
    from gc import collect
    # clean up any global variables here
    collect()
```

## Best Practices

1. Always handle BACK/LEFT buttons to allow users to exit
2. Call `input_manager.reset(True)` after handling each button press
3. Clean up all resources in the `stop()` function
4. Use global variables sparingly and clean them up properly
5. Test your app thoroughly before deployment

## Main GUI Components

### Draw
The `Draw` class is used for low-level drawing operations on the screen. It provides methods for drawing shapes, text, and images.
```python
from picoware.gui.draw import Draw
from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.vector import Vector

# create draw instance
draw = Draw()

# clear the screen
draw.clear(color=TFT_BLACK)

# draw some text
draw.text(
    Vector(10, 10),  # position
    "Hello, Picoware!",  # text
    TFT_WHITE  # color
)

# draw a rectangle
draw.rect(
    Vector(50, 50),  # position
    Vector(100, 50),  # size
    TFT_WHITE  # color
)

# draw a filled circle
draw.fill_circle(
    Vector(200, 150),  # position
    30,  # radius
    TFT_WHITE  # color
)

# swap the framebuffer to display the changes
draw.swap()
```

### List
Use the `List` component to display a scrollable list of items. It supports navigation and selection.
```python
from picoware.gui.draw import Draw
from picoware.gui.list import List
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE

# create draw instance
draw = Draw()

# create list instance
ls = List(
    draw, # draw instance
    0, # y position
    320, # height
    TFT_WHITE, # text color
    TFT_BLACK, # background color
    selected_color=TFT_BLUE, # selected item color
    border_color=TFT_WHITE, # border color
)

# add items to the list
ls.add_item("Item 1")
ls.add_item("Item 2")

# set the selected item
ls.set_selected(0)

# render the list
ls.draw()
```

### Menu
Use the `Menu` component to create a simple menu with selectable items.
```python
from picoware.gui.draw import Draw
from picoware.gui.menu import Menu
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE

# create draw instance
draw = Draw()

# create menu instance
menu = Menu(
    draw, # draw instance
    "menu", # title
    0, # y position
    320, # height
    TFT_WHITE, # text color
    TFT_BLACK, # background color
    selected_color=TFT_BLUE, # selected item color
    border_color=TFT_WHITE, # border color
)

# add items to the menu
menu.add_item("Item 1")
menu.add_item("Item 2")

# set the selected item
menu.set_selected(0)

# render the menu
menu.draw()
```

### TextBox
Use the `TextBox` component to display scrollable text. It supports word wrapping and can handle large amounts of text.
```python
from picoware.gui.draw import Draw
from picoware.gui.textbox import TextBox
from picoware.system.colors import TFT_WHITE

# sample text
text = """This is an example of a TextBox component in Picoware.
It supports word wrapping and can handle large amounts of text.
You can use it to display instructions, logs, or any other text content."""

# create draw instance
draw = Draw()

# create textbox instance
textbox = TextBox(draw, 0, 320, TFT_WHITE, TFT_BLACK)

# set and draw text
textbox.set_text(text)
```