# Updates
This details how to update Picoware on your device, specifically for the MicroPython OTA (Over The Air) update system.

> [!NOTE]
> This is only available in the MicroPython version of Picoware. For other versions, you will need to manually update by downloading the latest release from the repository and following the installation instructions.

## Overview
The MicroPython OTA update system allows you to update Picoware directly from your device without needing to connect it to a computer. Once the new version of Picoware is installed, you'll use [uf2loader](https://github.com/pelrun/uf2loader) to load the new uf2. Here's a [video guide](https://youtu.be/kErRrKBkjew?si=uNC3b_UJsbPvvyxc&t=193) that explains the process.

> [!NOTE]
> The uf2loader must be installed on your device for this update process to work. On your first install of the  uf2loader, place Picoware's uf2 file on the SD card, then use the bootloader menu to load Picoware. After that, you can follow the steps below to update Picoware in the future.

## Steps to Update
1. **Check for Updates**: Turn on your device, press `Enter` to open the `Library`, then navigate to `Settings` → `Check for Updates`. If an update is available, you will be prompted to download it.
2. **Download the Update**: Press `Enter` to download the update. The device will download the new version of Picoware and save it to the SD card.
3. **Enter Bootloader Mode**: After the download is complete, power off the device, then power it back on while holding the `Up` button to enter the `uf2loader` bootloader menu.
4. **Load the Update**: Scroll down and press `Enter` to select the downloaded uf2 file from the SD card and load it onto the device. The device will update to the new version of Picoware.