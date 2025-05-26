# Basics
This details the basic structure of Picoware's UI.

## Components
- Desktop
- Library
- System
- WiFi
- Games
- Screensavers

### Desktop
When you first power on the device, the `Desktop` view is what you're first presented with. It currently displays a 4-frame animation with your device type in the top-left corner and WiFi status in the top-right corner.

If you click the `Left` button, the `System Info` view will be displayed, which shows the core temperature and memory information. You can return to the Desktop by pressing `Left` or `Back`. 

### Library
If you click the `Up` or `Center` button on the `Desktop` view, the `Library` view will be displayed, which is a menu UI where users can select the `System`, `WiFi`, `Games`, or `Screensavers` view. As more categories are added, the list will be expanded (bluetooth, social media, etc).

### System
This menu has `About Picoware`, `System Info`, `Bootloader Mode`, and `Restart Device`. `About Picoware` has background information about Picoware and how to contact support. `System Info` shows the core temperature and memory information. `Bootloader Mode` will restart the device into bootloader mode. `Restart Device` will perform a quick soft-reset and return you to the `Desktop` view.

### WiFi
This menu has `Connect`, `Scan`, `Captive Portal`, and `Settings`. `Connect` is used to manage your WiFi networks. It can be used to connect and disconnect from your saved network. `Scan` is used to scan and display nearby WiFi networks. `Captive Portal` will create an access point named `Picoware` and handle connections. JBlanked plans to expand that once his PicoCalc arrives in the mail. Finally, `Settings` is where users type in and save their WiFi credentials to flash storage for later use.

### Games
This menu has a list of ready-to-play games (Doom, FlappyBird, Tetris, and more).

### Screensavers
This menu has a list of ready-to-see screensavers (Spiro, Starfield, and more).