# Installation

**Universal Method**
1. Download the appropiate build from the `builds` directory.
2. Press and hold the `BOOT` button on your device for 2 seconds.
3. While holding the `BOOT` button, connect the device to your computer using a USB cable.
4. Drag and drop the downloaded file onto the device. It will automatically reboot and begin running the example.

**Video Game Module (Only)**
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
12. The app will begin flashing the firmware to your Video Game Module. Wait until the process is complete.