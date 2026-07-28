# ThonnyIDE
This is a guide for using [ThonnyIDE](https://thonny.org) for development and debugging with Picoware.

## Debugging Firmware
You can debug the Picoware firmware using ThonnyIDE. Follow these steps to set up your environment:
1. Download the Picoware repository as a .zip from Github: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip
2. Unzip the downloaded file and open the `Picoware-main/src/MicroPython` folder in ThonnyIDE (by clicking `View` and making sure `Files` is checked, then navigating to the path in the `Files` tab).
3. Double-click the `main.py` file to open it in the editor.
4. Click the "Run" button in the top menu to run the firmware on your device. The REPL output will contain debugging and runtime information when navigating through the firmware and applications. 

## Testing Applications
You can test your application within the IDE by simulating the `ViewManager` object. Here's how to set up your application for testing:

1. Paste your application code to a new file within ThonnyIDE. 
2. Add the following code snippet to the bottom of your application file:

```python
# your start, run, stop functions here

# add this at the bottom of your app for testing
from picoware.system.view_manager import ViewManager
from picoware.system.view import View
from picoware.system.app_loader import AppLoader

vm = None

try:
    vm = ViewManager()
    loader = AppLoader(vm)
    loader.load_module("/picoware/apps")
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
finally:
    del vm
    vm = None
```

3. Click the "Run" button in the top menu to run your application. 

## Videos
- My PicoCalc Workflow: Picoware Debugging With VS Code and Thonny IDE: https://youtu.be/_Yu3Op-nhyc
- PicoCalc Development with Thonny IDE and MicroPython: Your Ideal Duo: https://youtu.be/I8E6u60ePL0