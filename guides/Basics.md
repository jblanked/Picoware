# Basics
This details the basic structure of Picoware's MicroPython UI.

## Components
- Desktop
- Library
- Applications
- App Store
- Bluetooth
- File Manager
- GameBoy Emulator
- Games
- Python Editor
- Python REPL
- Screensavers
- System
- Text Editor
- USB
- WiFi

### Desktop
When you first power on the device, the `Desktop` view is what you're first presented with. It currently displays a 4-frame animation with your device type in the top-left corner and WiFi status in the top-right corner.

If you click the `Left` button, the `System Info` view will be displayed, which shows the core temperature and memory information. You can return to the Desktop by pressing `Left` or `Back`. 

### Library
If you click the `Up` or `Center` button on the `Desktop` view, the `Library` view will be displayed. It is a scrollable menu listing all available categories: `Applications`, `App Store`, `Bluetooth`, `File Manager`, `GameBoy Emulator`, `Games`, `Python Editor`, `Python REPL`, `Screensavers`, `System`, `Text Editor`, `USB`, and `WiFi`. Use `Up`/`Down` (or `Left`/`Right`) to scroll through the list, `Center` to open the highlighted category, and `Back` to return to the Desktop.

### Applications
This menu has a list of applications that are ready to use. It is populated by apps that are installed on your SD card or downloaded from the App Store. Use `Up`/`Down` (or `Left`/`Right`) to scroll through the list, `Center` to launch the highlighted app, and `Back` to return to the Library.

### App Store
The App Store requires both a WiFi connection and an SD card. It connects to the Picoware app repository and lets you browse, install, and update third-party apps directly on your device. The main menu has three options: `Update Apps` checks all installed apps for newer versions, `Current App Info` lists your installed apps (press `Left` on an app's detail page to delete it, or `Center` to check for/apply an update), and `Browse App Store` fetches the full catalog from the server. While browsing, use `Up`/`Down` (or `Left`/`Right`) to scroll, `Center` to view an app's details or install it, and `Back` to return to the previous screen. A `Download All Apps` option at the top of the catalog installs every available app in sequence.

### Bluetooth
This menu has `Classic Scan`, `BLE Scan`, `BLE Keyboard`, and `BLE Mouse`. `Classic Scan` is used to scan for classic Bluetooth devices. `BLE Scan` is used to scan for Bluetooth Low Energy devices. `BLE Keyboard` allows your device to act as a peripheral keyboard, and `BLE Mouse` allows it to act as a peripheral mouse.

### File Manager
The File Manager requires an SD card. It opens a full file browser rooted at your SD card, allowing you to navigate folders, view text files and images, and manage files. Use `Up`/`Down` to move the selection, `Center` to open a folder or file, and `Back` to go up one directory or exit.

### GameBoy Emulator
The GameBoy Emulator requires PSRAM. On launch it displays a key-mapping reference screen — press any button (other than `Back`) to proceed. You are then presented with a file browser to select a `.gb` or `.gbc` ROM from your SD card. Once a ROM is loaded, the emulator runs at up to 60 FPS. The PicoCalc keyboard maps to the GameBoy controls as follows:

| PicoCalc key | GameBoy button |
|---|---|
| Arrow Up | Up |
| Arrow Down | Down |
| Arrow Left | Left |
| Arrow Right | Right |
| `]` | A |
| `[` | B |
| `=` | Start |
| `-` | Select |

Press `Back` during gameplay to stop the emulator and return to the Library.

### Games
This menu has a list of ready-to-play games (Doom, FlappyBird, Tetris, and more).

### Python Editor
The Python Editor requires an SD card. On launch you choose between `Create New File` and `Edit Existing App`. If creating a new file, the on-screen keyboard appears so you can type a filename; after confirming, you pick the file type (`Picoware App` to generate a starter template, or `Python Script` for a blank file). If editing an existing app, a file browser opens starting in `picoware/apps` so you can select the file. Either path then opens the `pye` editor — a full-featured terminal-based text editor. 

Press `Back` to save and exit the editor and return to the Library.

### Python REPL
The Python REPL is an interactive Python shell that runs directly on the device. It displays a `>>>` prompt and evaluates expressions or executes statements as you type. Multi-line blocks (functions, loops, `if` statements, etc.) are detected automatically — the prompt changes to `...` and you continue entering lines until you submit a blank line to run the block. Type `clear` and press `Center` to reset the screen. Press `Back` to exit.

| Button | Action |
|---|---|
| Keyboard | Type Python code |
| `Center` | Execute current input |
| `Back` | Exit REPL |

### Screensavers
This menu has a list of ready-to-see screensavers (Spiro, Starfield, and more).

### System
This menu has `About Picoware`, `System Info`, `Bootloader Mode`, and `Restart Device`. `About Picoware` has background information about Picoware and how to contact support. `System Info` shows the core temperature and memory information. `Bootloader Mode` will restart the device into bootloader mode. `Restart Device` will perform a quick soft-reset and return you to the `Desktop` view.

### Text Editor
The Text Editor is a plain-text file editor for reading and writing any file on flash or SD card. On launch you choose between `Create New File` and `Select File`. Selecting `Create New File` opens the on-screen keyboard so you can type a filename; confirming the name opens a blank document. Selecting `Select File` opens a file browser starting at the root directory so you can choose an existing file to edit.

Inside the editor, the full keyboard is available for typing. Navigation and editing controls are:

| Button / Key | Action |
|---|---|
| Arrow keys | Move cursor one character/line |
| `Ctrl+Up` | Jump to beginning of file |
| `Ctrl+Down` | Jump to end of file |
| `Backspace` | Delete character before cursor |
| `Back` | Save file and return to the Text Editor menu |

### USB
The USB menu is a hub for USB HID peripherals. It contains three sub-apps: `Keyboard`, `Media Keys`, and `Numpad`. Use `Up`/`Down` (or `Left`/`Right`) to highlight an option, `Center` to launch it, and `Back` to return to the Library. Each sub-app turns the device into the corresponding USB HID device — a full keyboard, media-control keys (play/pause, volume, etc.), or a numeric keypad — so it can be used with any connected host computer.

### WiFi
This menu has `Connect`, `Scan`, `Captive Portal`, and `Settings`. `Connect` is used to manage your WiFi networks. It can be used to connect and disconnect from your saved network. `Scan` is used to scan and display nearby WiFi networks. `Captive Portal` will create an access point named `Picoware` and handle connections. Finally, `Settings` is where users type in and save their WiFi credentials to flash storage for later use.