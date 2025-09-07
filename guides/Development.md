# Development

The firmware is available for the Arduino IDE (C++), CircuitPython, and C/C++ (using the official SDK). Each environment offers similar configurations, methods, and functionalities to ensure a smooth development experience.

### C/C++ SDK

Here's a video tutorial: https://youtu.be/-eMqPjVN0fU?si=obkQ3QTTLtz72qeE&t=569

### Arduino IDE

To use the Arduino IDE library:
1. Install the Arduino IDE from https://www.arduino.cc/en/software.
2. Download this repository as a .zip file (available here: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip).
3. Within the `src/ArduinoIDE` folder, right-click the `Picoware` folder and select `Copy`.
4. Navigate to your Arduino libraries folder (usually at `../../Documents/Arduino/libraries` or `../Arduino/libraries`) and paste the folder there.
5. Open the Arduino IDE you downloaded earlier, go to Preferences/Settings, and add the following URL to the `Additional Boards Manager URLs` field: `https://github.com/earlephilhower/arduino-pico/releases/download/4.7.1/package_rp2040_index.json`. Click `OK`.
6. In `Boards Manager`, search for `rp2040` and install the `Raspberry Pi Pico/RP2040/RP2350` package.
7. In `Library Manager`:
- Search for `TFT_eSPI` and install the `TFT_eSPI` library by `Bodmer`.
- Search for `PicoDVI` and install the `PicoDVI - Adafruit Fork` by `Luke Wren (Wren6991)` (it may show up as by `Adafruit`). 
- Search for `AsyncHTTPRequest_RP2040W` and install the `AsyncHTTPRequest_RP2040W` library by `Bob Lemaire, Khoi Hoang`.
- Search for `ArduinoJson` and install the `ArduinoJson` library by `Benoit Blanchon`.
- Search for `ArduinoHttpClient` and install the `ArduinoHttpClient` library by `Arduino`.
8. Close your Arduino IDE. Within the `src/ArduinoIDE` folder (from earlier), double-click the `ArduinoIDE.ino` file.
9. Hold the `BOOT` button while connecting your `Micro USB` data cable to your `Raspberry Pi Pico` device.
10. Select the serial port to which your Pico is connected and choose your specific Pico type (e.g., `Raspberry Pi Pico`) as your board.
11. In line 13, change the board configuration (e.g., `VGMConfig`, `PicoCalcConfigPico`, etc.) to your specific configuration.
- `VGMConfig`: Video Game Module
- `JBlankedPicoConfig`: JBlanked's Custom Pico Setup
- `PicoCalcConfigPico`: PicoCalc (with a Raspberry Pi Pico)
- `PicoCalcConfigPicoW`: PicoCalc (with a Raspberry Pi Pico W)
- `PicoCalcConfigPico2`: PicoCalc (with a Raspberry Pi Pico 2)
- `PicoCalcConfigPico2W`: PicoCalc (with a Raspberry Pi Pico 2 W)

12. Open the `User_Setup.h` file in the `TFT_eSPI` library folder (usually located at `../../Documents/Arduino/libraries/TFT_eSPI/User_Setup.h` or `../Arduino/libraries/TFT_eSPI/User_Setup.h`) and:

Replace it with the following code snippet if you're using the PicoCalc:
```cpp
#define USER_SETUP_ID 60
#define ILI9488_DRIVER
#define TFT_RGB_ORDER TFT_BGR
#define TFT_MISO 12
#define TFT_MOSI 11
#define TFT_SCLK 10
#define TFT_CS 13
#define TFT_DC 14
#define TFT_RST 15
#define TFT_SPI_PORT 1
#define SPI_FREQUENCY 25000000
#define SPI_TOUCH_FREQUENCY 2500000
#define LOAD_GLCD
#define LOAD_FONT2
#define SMOOTH_FONT
#define TFT_INVERSION_ON
```

Replace it with the following code snippet if you're using JBlanked's Custom Pico Setup:
```cpp
#define USER_SETUP_INFO "User_Setup"
#define ILI9341_DRIVER
#define TFT_BL 32             // LED back-light control pin
#define TFT_BACKLIGHT_ON HIGH // Level to turn ON back-light (HIGH or LOW)
#define TFT_MISO 4
#define TFT_CS 5 
#define TFT_SCLK 6
#define TFT_MOSI 7
#define TFT_RST 10 
#define TFT_DC 11  
#define TOUCH_CS 21 
#define LOAD_GLCD
#define LOAD_FONT2
#define SMOOTH_FONT
#define SPI_FREQUENCY 27000000
#define SPI_READ_FREQUENCY 20000000
#define SPI_TOUCH_FREQUENCY 2500000
```

13. In `Tools` menu, change the `Flash Size` to `2MB (Sketch: 1984KB, FS: 64KB)` (or `4MB (Sketch: 4032KB, FS: 64KB)` if compiling for a Raspberry Pi Pico 2 or 2W device) and `CPU Speed` to `200MHz`. Then change `IP/Bluetooth Stack` to `IPv4 + Bluetooth` if you are not compiling for a non-Pico-W device, otherwise leave it on the default, `IPv4`.
14. Finally, click `Sketch` in the menu, then select `Upload`.

Here's a video tutorial: https://www.youtube.com/watch?v=-eMqPjVN0fU

### MicroPython

To use MicroPython library:
1. Download and install Thonny IDE (https://thonny.org).
2. Install the Micropython SDK:
'''
sudo apt install gcc-arm-none-eabi
mkdir ~/pico
cd ~/pico
git clone https://github.com/micropython/micropython.git
git clone https://github.com/micropython/micropython-lib.git
cd micropython
git submodule update --init
make -C mpy-cross
'''
3. Download this repository as a .zip file (available here: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip).
4. In the `src/MicroPython` folder, copy the entire picoware and picoware_lcd folder into `~/pico/micropython/ports/rp2/modules`
5. Now, build the MicroPython firmware with:
'''
# Pico
cd ~/pico/micropython/ports/rp2
make clean
make BOARD=RPI_PICO USER_C_MODULES=~/pico/micropython/ports/rp2/modules/picoware_lcd/micropython.cmake

# Pico W
cd ~/pico/micropython/ports/rp2
make clean
make BOARD=RPI_PICO_W USER_C_MODULES=~/pico/micropython/ports/rp2/modules/picoware_lcd/micropython.cmake

# Pico 2
cd ~/pico/micropython/ports/rp2
make clean
make BOARD=RPI_PICO2 USER_C_MODULES=~/pico/micropython/ports/rp2/modules/picoware_lcd/micropython.cmake

# Pico 2W
cd ~/pico/micropython/ports/rp2
make clean
make BOARD=RPI_PICO2_W USER_C_MODULES=~/pico/micropython/ports/rp2/modules/picoware_lcd/micropython.cmake
'''

### CircuitPython

Developers can also use CircuitPython, although due to limited memory, they must be more conservative with memory usage and strategically handle text objects.

1. Download and install Thonny IDE (https://thonny.org).
2. Download this repository as a .zip file (available here: https://github.com/jblanked/Picoware/archive/refs/heads/main.zip).
3. Press and hold the `BOOT` button on your `Raspberry Pi Pico` device for 2 seconds.
4. While holding the `BOOT` button, connect your `Raspberry Pi Pico` device to your computer using a `Micro USB` cable.
5. Open Thonny, and in the bottom-right corner, select `Install CircuitPython`.
6. Change the settings to your specific Raspberry Pi Pico type and proceed with the installation.
7. Once finished, close the window and press the red `Stop/Restart` button.
8. Afterward, open the .zip file downloaded earlier and navigate to the `src/CircuitPython` folder. Copy and paste all contents of that folder into your `CIRCUITPY` drive that appeared after CircuitPython finished installing.
9. In Thonny, press the `Stop/Restart` button again, then double-click the `code.py` file on your `CIRCUITPY` drive and click the green `Start/Run` button.
