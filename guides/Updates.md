# Updates
This details how to update Picoware on your device, specifically for the MicroPython OTA (Over The Air) update system.

> [!NOTE]
> This is only available in the MicroPython version of Picoware. For other versions, you will need to manually update by downloading the latest release from the repository and following the installation instructions.

## Overview
Picoware has an automatic update and install system for rp2040/rp2350 devices. The `Desktop` view checks for updates automatically when you open it, and will prompt you to download the latest version if one is available. You can also check for updates manually by clicking the `Check for Updates` button in the `Settings` menu.

## Steps to Update
1. **Check for Updates**: Turn on your device, press `Enter` to open the `Library`, then navigate to `Settings` → `Check for Updates`. If an update is available, you will be prompted to download it.
2. **Download the Update**: Press `Enter` to download the update. The device will download the new version of Picoware and save it to the SD card.
3. **Enter Bootloader Mode**: After the download is complete, Picoware will attempt to install the update and restart. If the device does not restart automatically, restart it manually and the update will be applied. If the update fails, you may need to reinstall the firmware using the method described in the [Installation Guide](Installation.md#installing-picoware).