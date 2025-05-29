# Development

The firmware is available for the Arduino IDE (C++), CircuitPython, and C/C++ (using the official SDK). Each environment offers similar configurations, methods, and functionalities to ensure a smooth development experience.

### Arduino IDE

To use the Arduino IDE library:
1. Install the Arduino IDE from https://www.arduino.cc/en/software.
2. Download this repository as a .zip file (available here: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip).
3. Within the `src/ArduinoIDE` folder, right-click the `Picoware` folder and select `Copy`.
4. Navigate to your Arduino libraries folder (usually at `../../Documents/Arduino/libraries`) and paste the folder there.
5. Open the Arduino IDE you downloaded earlier, go to Preferences/Settings, and add the following URL to the `Additional Boards Manager URLs` field: `https://github.com/earlephilhower/arduino-pico/releases/download/4.5.3/package_rp2040_index.json`. Click `OK`.
6. In `Boards Manager`, search for `rp2040` and install the `Raspberry Pi Pico/RP2040/RP2350` package.
7. In `Library Manager`, search for `TFT_eSPI` and install the `TFT_eSPI` library by `Bodmer`. Then search for `PicoDVI` and install the `PicoDVI - Adafruit Fork` by `Luke Wren (Wren6991)`.
8. Close your Arduino IDE. Within the `src/ArduinoIDE` folder (from earlier), double-click the `ArduinoIDE.ino` file.
9. Hold the `BOOT` button while connecting your USB data cable.
10. Select the serial port to which your Pico is connected and choose your specific Pico type (e.g., `Raspberry Pi Pico`) as your board.
11. In line 13, change the board configuration (e.g., `VGMConfig`, `PicoCalcConfigPico`, etc.) to your specific configuration.
12. In `Tools` menu, change the `Flash Size` to `2MB (Sketch: 1984KB, FS: 64KB)` and `CPU Speed` to `200MHz`. Then change `IP/Bluetooth Stack` to `IPv4 + Bluetooth` if you are not compiling for a non-Pico-W device, otherwise leave it on the default, `IPv4`.
13. Finally, click `Sketch` in the menu, then select `Upload`.

### CircuitPython

Developers can also use CircuitPython, although due to limited memory, they must be more conservative with memory usage and strategically handle text objects.

1. Download and install Thonny IDE (https://thonny.org).
2. Download this repository as a .zip file (available here: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip).
3. Press and hold the `BOOT` button on your device for 2 seconds.
4. While holding the `BOOT` button, connect the device to your computer using a USB cable.
5. Open Thonny, and in the bottom-right corner, select `Install CircuitPython`.
6. Change the settings to your specific Raspberry Pi Pico type and proceed with the installation.
7. Once finished, close the window and press the red `Stop/Restart` button.
8. Afterward, open the .zip file downloaded earlier and navigate to the `src/CircuitPython` folder. Copy and paste all contents of that folder into your `CIRCUITPY` drive that appeared after CircuitPython finished installing.
9. In Thonny, press the `Stop/Restart` button again, then double-click the `code.py` file on your `CIRCUITPY` drive and click the green `Start/Run` button.

### C/C++ SDK

This integration is not yet available.
