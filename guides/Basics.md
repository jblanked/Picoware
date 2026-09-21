# Basics
This details the basic structure of Picoware's MicroPython UI.

## Components
- Desktop
- Library
  - Applications (`Agent`, `App Store`, `C`, `Custom`, `FlipSocial`, `Games`, `JavaScript`, `MMBasic`, `Screensavers`)
  - Bluetooth (`Scan Devices`, `Advertise`, `Pair Device`, `UART Chat`, `Beacon`, `RSSI Monitor`)
  - Infrared (`Remote`, `Learn`, `Settings`)
  - Settings
  - System (`Update`, `About`, `System Info`, `Bootloader`, `Restart`, `Shutdown`, `Stop`)
  - USB (`Numpad`, `Media Keys`, `Payload`, `Keyboard`)
  - Utilities (`Email`, `File Manager`, `PicoIDE`, `Python REPL`, `Serial Terminal`, `SSH Terminal`)
  - WiFi (`Connect`, `RSSI Monitor`, `Scan`, `Server`, `Settings`)

### Desktop
When you first power on the device, the `Desktop` view is what you're first presented with. It shows an animated `Picoware` splash with a header bar containing your device name, the current time, WiFi and Bluetooth icons, and the battery level.

| Button | Action |
|---|---|
| `Center` | Open the `Library` |
| `Up` | Open `Notifications`, which lists FlipSocial, weather, and email notifications (requires WiFi and an SD card) |
| `Left` | Open `System Info`, which shows the core temperature and memory information |

You can return to the Desktop by pressing `Back`, or `Left`/`Back` from `System Info`.

### Library
If you press `Center` on the `Desktop` view, the `Library` view will be displayed. It is a scrollable menu listing all top-level categories: `Applications`, `Bluetooth`, `Infrared`, `Settings`, `System`, `USB`, `Utilities`, and `WiFi`. Use `Up`/`Down` (or `Left`/`Right`) to scroll through the list, `Center` to open the highlighted category, and `Back` to return to the Desktop.

#### Applications
This menu holds the app hubs and language runtimes: `Agent`, `App Store`, `C`, `Custom`, `FlipSocial`, `Games`, `JavaScript`, `MMBasic`, and `Screensavers`. Use `Up`/`Down` (or `Left`/`Right`) to scroll through the list, `Center` to open the highlighted item, and `Back` to return to the Library.

- `Agent` opens the Picoware AI assistant with `Chat`, `App Creator`, `Device Manager`, `Sessions`, and `Settings` (provider, model, and thinking level).
- `App Store` browses, installs, and updates apps from the Picoware repository (requires WiFi and an SD card).
- `C` lists and runs compiled C programs from `picoware/c`.
- `Custom` lists and runs MicroPython apps installed in `picoware/apps`.
- `FlipSocial` opens the FlipSocial client (requires WiFi and an SD card).
- `Games` lists the built-in games plus any games in `picoware/apps/games`.
- `JavaScript` lists and runs scripts from `picoware/scripts`.
- `MMBasic` lists and runs programs from `picoware/mmbasic`.
- `Screensavers` lists and runs screensavers from `picoware/apps/screensavers`.

##### App Store
The App Store requires both a WiFi connection and an SD card. It connects to the Picoware app repository and lets you browse, install, and update third-party apps directly on your device. The main menu has `Update Apps` (checks all installed apps for newer versions), `Downloaded Apps` (lists your installed apps — press `Left` on an app's detail page to delete it, or `Center` to check for/apply an update), the browse categories (`View All`, `View Python Apps`, `View JS Scripts`, `View MMBasic Programs`, `View C Programs`), `Submit App`, `App Submissions`, and `Settings`. While browsing, use `Up`/`Down` (or `Left`/`Right`) to scroll, `Center` to view an app's details or install it, and `Back` to return to the previous screen. A `[Download All]` option at the top of a category installs every available app in sequence.

##### GameBoy Emulator
The GameBoy Emulator requires PSRAM and a PicoCalc. On launch it displays a key-mapping reference screen — press any button (other than `Back`) to proceed. You are then presented with a file browser to select a `.gb` or `.gbc` ROM from your SD card. Once a ROM is loaded, the emulator runs at up to 60 FPS. The PicoCalc keyboard maps to the GameBoy controls as follows:

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

Press `Back` during gameplay to stop the emulator and return to the Games menu.

#### Bluetooth
This menu has `Scan Devices`, `Advertise`, `Pair Device`, `UART Chat`, `Beacon`, and `RSSI Monitor`. `Scan Devices` scans for nearby Bluetooth devices, `Advertise` makes the device discoverable, `Pair Device` pairs with a discovered device, `UART Chat` opens a Bluetooth UART chat, `Beacon` broadcasts the device as a beacon, and `RSSI Monitor` shows live signal strength. Requires a Bluetooth-capable board.

#### Infrared
This menu has `Remote`, `Learn`, and `Settings`. `Remote` lists the `.ir` remote files under the SD card's `infrared/` directory — open a remote, highlight a signal name, and press `Center` to transmit it. `Learn` captures an incoming signal: choose the `Button` and `Name` fields, then select `Listen`, and the captured signal is saved as a raw `.ir` file. `Settings` has `Use External?` and `Pin` for boards that use an external IR transmitter.

IR support depends on the board: the Flipper Zero transmits and receives, the Cardputer-Adv transmits only, and other boards need external IR hardware. See [Infrared](Infrared.md) for the file format and API.

#### Settings
This menu holds device-wide preferences: `Anthropic API Key`, `Dark Mode`, `Debug`, `DeepSeek API Key`, `Exit Button`, `Gemini API Key`, `JBlanked API Key`, `Local API Key`, `Local URL`, `MCP Servers`, `Onscreen Keyboard`, `OpenAI API Key`, `Screen Brightness`, `Server Settings`, `Theme Color`, `Time`, `USB Stream`, `Use LVGL`, and `xAI API Key`. Use `Up`/`Down` to scroll, `Center` to change the highlighted setting, and `Back` to return to the Library.

#### System
This menu has `Update`, `About`, `System Info`, `Bootloader`, `Restart`, `Shutdown`, and `Stop`. `Update` checks for and downloads a new firmware update. `About` has background information about Picoware and how to contact support. `System Info` shows the core temperature and memory information. `Bootloader` restarts the device into bootloader mode. `Restart` performs a quick soft-reset and returns you to the `Desktop` view. `Shutdown` asks for confirmation and powers the device off. `Stop` exits the Picoware UI and returns to the MicroPython REPL.

#### USB
The USB menu turns the device into a USB HID peripheral. It contains `Numpad`, `Media Keys`, `Payload`, and `Keyboard`. Use `Up`/`Down` (or `Left`/`Right`) to highlight an option, `Center` to launch it, and `Back` to return to the Library. `Keyboard` exposes a full keyboard, `Media Keys` exposes media-control keys (play/pause, volume, etc.), `Numpad` exposes a numeric keypad, and `Payload` runs DuckyScript payloads from the SD card over USB.

#### Utilities
The Utilities menu groups the file, email, and terminal tools: `Email`, `File Manager`, `PicoIDE`, `Python REPL`, `Serial Terminal`, and `SSH Terminal`.

`Email` sends and reads email over SMTP and IMAP (requires WiFi and an SD card). `File Manager` requires an SD card; it opens a full file browser rooted at your SD card, allowing you to navigate folders, view text files and images, and manage files. Use `Up`/`Down` to move the selection, `Center` to open a folder or file, and `Back` to go up one directory or exit.

`PicoIDE` requires an SD card. On launch you choose between `Create New File` and `Edit Existing File`. If creating a new file, the on-screen keyboard appears so you can type a filename; after confirming, you pick the file type (`Python App`, `C Source File`, `JavaScript Script`, `MMBasic Program`, or `Text File`). If editing an existing file, a file browser opens starting in `picoware/apps` so you can select the file. Either path then opens the `pye` editor — a full-featured terminal-based text editor. Press `Back` to save and exit, or press `F5` to run the current file.

`Python REPL` is an interactive Python shell that runs directly on the device. It displays a `>>>` prompt and evaluates expressions or executes statements as you type. Multi-line blocks (functions, loops, `if` statements, etc.) are detected automatically — the prompt changes to `...` and you continue entering lines until you submit a blank line to run the block. Type `clear` and press `Center` to reset the screen. Press `Back` to exit.

| Button | Action |
|---|---|
| Keyboard | Type Python code |
| `Center` | Execute current input |
| `Back` | Exit REPL |
| `Up` | Cycle through previous commands |
| `Down` | Cycle through next commands |

`Serial Terminal` opens a UART terminal for sending and receiving serial data. `SSH Terminal` is an SSH client for connecting to remote hosts (requires WiFi and an SD card).

#### WiFi
This menu has `Connect`, `RSSI Monitor`, `Scan`, `Server`, and `Settings`. `Connect` manages your WiFi networks and can connect and disconnect from your saved network. `RSSI Monitor` displays live signal strength. `Scan` scans and displays nearby WiFi networks. `Server` hosts a web server with editable pages. `Settings` is where you type in and save your WiFi credentials to flash storage for later use.