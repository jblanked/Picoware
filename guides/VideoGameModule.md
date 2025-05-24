## About
The Video Game Module is a device by Flipper Devices, released in 2024. Initially designed for screen mirroring the Flipper Zero’s display to a TV or monitor, it includes a built-in gyroscope and accelerometer, a USB-C port, a 14-pin GPIO header, and a DVI port. Learn more: https://shop.flipperzero.one/products/video-game-module-for-flipper-zero

## Game Usage
To get started, flash your Video Game Module with an example or your own custom script, then install the companion app on your Flipper Zero. The module handles video output and the game engine, while the Flipper Zero serves as a controller—reversing their traditional roles. Developers can create new games or port existing Flipper titles, taking advantage of increased memory, full-color graphics, and output to an external display.

### Flipper Zero App
The Flipper Zero app lets you use the D-pad as input for games built with the engine. The source code resides in `src/FlipperZeroApp`. Use [ufbt](https://github.com/flipperdevices/flipperzero-ufbt) to compile it into a `.fap` file, or install it directly on your Flipper Zero from https://lab.flipper.net/apps/vgm_game_remote
