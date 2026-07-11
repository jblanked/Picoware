# Installation

> [!WARNING]
> If you're using PicoCalc, make sure to update your keyboard firmware first: https://github.com/jblanked/awesome-pico-calc/blob/master/GettingStarted.md#updating-the-stm32>

## PicoCalc, Waveshare, and other Raspberry Pi Pico-based boards
1. Download the appropiate build from the `builds` directory.
2. Press and hold the `BOOT` button on your Raspberry Pi Pico/W or Pico 2/2W.
3. While holding the `BOOT` button, connect the Pico to your computer using a USB cable (that supports data transfer) until your computer recognizes a new storage device.
4. Drag and drop the downloaded file onto the device that appears (it should be named `RPI-RP2` if using a Raspberry Pi Pico/W or `RP2350` if using a Raspberry Pi Pico 2/2W). 
5. Once the file transfer is complete, the Pico will eject itself. Disconnect the USB cable from your Pico.

> [!NOTE]
> If you are installing the MicroPython version, copy the `apps` folder from `builds/MicroPython` to the `picoware` folder on your SD card. Create a `picoware` folder if it doesn't exist.

> [!NOTE]
> If you are installing the CircuitPython version, after installing Picoware, replace the `code.py` file on your Pico with the one from `src/CircuitPython`. Then, copy the `apps` folder from `builds/CircuitPython` to the `picoware` folder on your SD card. Create a `picoware` folder if it doesn't exist.

## Video Game Module (Only)
1. Install the Video Game Module Tool app on your Flipper Zero from the Apps catalog: [Video Game Module Tool](https://lab.flipper.net/apps/video_game_module_tool).
2. Download the `Picoware-VGM.uf2` from the `builds` directory.
3. Disconnect your Video Game Module from your Flipper and connect your Flipper to your computer.
4. Open qFlipper.
5. Navigate to the `SD Card/apps_data/vgm/` directory. If the folder doesn’t exist, create it. Inside that folder, create a folder named `Picoware`.
6. Drag the `Picoware-VGM.uf2` file you downloaded earlier into the `Picoware` directory.
7. Disconnect your Flipper from your computer, then turn it off.
8. Connect your Video Game Module to your Flipper, then turn your Flipper on.
9. Open the Video Game Module Tool app on your Flipper. It should be located in the `Apps -> Tools` folder from the main menu.
10. In the Video Game Module Tool app, select `Install Firmware from File`, then choose `apps_data`.
11. Scroll down and click on the `vgm` folder, then the `Picoware` folder, and finally select the `Picoware-VGM.uf2` file.
12. The app will begin flashing Picoware to your Video Game Module. Wait until the process is complete.

## M5Stack Cardputer ADV

There are a few options for installing Picoware on the M5Stack Cardputer ADV.

The recommended way is to use M5Burner to install an app called `M5Launcher` that allows you to flash custom firmware to your Cardputer on-the-fly:
1. Download, install, and open the M5Burner tool from the official M5Stack website: https://docs.m5stack.com/en/download
2. Under `Device Type`, select `Cardputer`.
3. Type in `M5Launcher` in the search bar, then click `Download` next to the M5Launcher firmware.
4. Turn off your Cardputer, then hold the `Go` button on your Cardputer while connecting it to your computer using a USB-C cable until your computer recognizes a new storage device.
5. In M5Burner, click `Burn`, then `Continue`, then change the `COM Port` to the one that corresponds to your Cardputer, and click `Start`.
6. Wait until the flashing process is complete, then disconnect your Cardputer from your computer and turn it on. M5Launcher should now be installed and ready to use!
7. Download the `Picoware-Cardputer.bin` file from the `builds/MicroPython` directory of this repository and copy it to the root of your SD card.
8. With your Cardputer off, insert the SD card into your Cardputer, then turn on your device.
9. Once the app is open, click `SD` then scroll down and select the `Picoware-Cardputer.bin` file, then click `Install`. 
10. Wait until the installation process is complete and your Cardputer will reboot into Picoware!

> [!NOTE]
> If the recommended installation method doesn't work for you, follow the instructions below, otherwise proceed with copying the `apps` folder from `builds/MicroPython` to the `picoware` folder on your SD card.

The second option is to use the M5Burner tool provided by M5Stack to install Picoware directly to your Cardputer:
1. Download, install, and open the M5Burner tool from the official M5Stack website: https://docs.m5stack.com/en/download
2. Under `Device Type`, select `Cardputer`.
3. Type in `Picoware` in the search bar, then click `Download` next to the Picoware firmware.
4. Turn off your Cardputer, then hold the `Go` button on your Cardputer while connecting it to your computer using a USB-C cable until your computer recognizes a new storage device.
5. In M5Burner, click `Burn`, then `Continue`, then change the `COM Port` to the one that corresponds to your Cardputer, and click `Start`.
6. Wait until the flashing process is complete, then disconnect your Cardputer from your computer and turn it on. Picoware should now be installed and ready to use!


The third option is to just download the `Picoware-Cardputer.bin` file from the `builds/MicroPython` directory and flash it to your Cardputer using your favorite flashing tool.

The fourth option is to download (and extract) this repository as a ZIP file, then update the environment variables within the `tools/micropython-cardputer-flash.sh` script to match your setup, and run the script. You need to pass the port that your Cardputer is connected to as an argument when running the script (`--port COM3` for example).

## Elecrow CrowPanel
1. Download this repository as a ZIP file and extract it.
2. Update the environment variables within the `tools/micropython-crowpanel-flash.sh` script to match your setup.
3. Connect a USB-C cable to your `USB 2.0` port on your CrowPanel and connect the other end to a power source. Do not connect the cable to your computer, as the `USB 2.0` port is for power only.
4. Connect another USB-C cable to the `UART0` port on your CrowPanel and connect the other end to your computer.
5. Run the `tools/micropython-crowpanel-flash.sh` script.

Optionally, you can also download the `Picoware-CrowPanel-10.1.bin` file from the `builds/MicroPython` directory and flash it to your CrowPanel using your favorite flashing tool.
