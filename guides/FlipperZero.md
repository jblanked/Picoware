## About
The [Flipper Zero](https://flipper.net/products/flipper-zero) is a device by Flipper Devices, released in 2020. It is a portable multi-tool for pentesters and geeks, featuring a variety of built-in hardware modules such as RFID, infrared, GPIO, and more, allowing users to interact with and control a wide range of electronic devices.


## Usage

### On-screen keyboard

The up arrow is Shift; the arrow with a bar below it is Caps Lock. An underline
across either key indicates that the modifier is active. Use the D-pad to select
a key and the center button to press it. SPACE inserts a space; SAVE submits the
entered text.

### Bootloader Mode
Bootloader mode, also known as DFU or download mode, allows you to flash firmware or perform low-level maintenance on the device. To enter bootloader mode within Picoware, navigate to `Library -> System -> Bootloader`. Then you can use an application like `qFlipper` to flash firmware or perform other maintenance tasks.

### UART WiFi and WebSocket
Using a [FlipperHTTP](https://github.com/jblanked/FlipperHTTP) flashed board, you can give your Flipper Zero WiFi and WebSocket access within Picoware by connecting a compatible WiFi module to the Flipper Zero's GPIO pins. Once connected, you can access WiFi settings in `Library -> WiFi`. Here, you can configure your network, scan for available networks, and manage your WiFi connections.