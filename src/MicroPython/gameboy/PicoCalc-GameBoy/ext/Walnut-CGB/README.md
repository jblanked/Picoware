Walnut-CGB is a single file header Game Boy/Gameboy Color emulator library based off of the more portable [Peanut-GB](https://github.com/deltabeard/Peanut-GB).
This is a full reimplementation of the core to support native 16-bit and 32-bit operations, processing instructions with a [dual-fetch chained architecture](https://github.com/Mr-PauI/Walnut-CGB/wiki/CPU-opcode-dispatch-model). A significant deviation from the Peanut-GB cpu opcode dispatch model. See [Migrating from Peanut-GB](https://github.com/Mr-PauI/Walnut-CGB/wiki/Migrating-from-Peanut%E2%80%90GB) for details for porting existing implementations.

<img width="128" height="128" alt="WalnutCGB" src="https://github.com/user-attachments/assets/77e4290b-858b-4f64-bf6a-69d56f76c8e1" />   

It includes all DMG updates from its main branch as well as the CGB support fork integrated into it. Additional bugs have been fixed and, when appropriate, have been submitted upstream to the Peanut-GB project in the [upstream-changes](https://github.com/Mr-PauI/Walnut-CGB/tree/upstream-changes) branch.

## Features

- Game Boy (DMG) & Game Boy Color (CGB) Support
- MBC1, MBC2, MBC3, MBC30 and MBC5 support
- Real Time Clock (RTC) support
- Serial connection support
- Can be used with or without a bootrom
- Allows different palettes on background and sprites (3 layers x 4 shades = 12 colors)
- Simple to use and comes with examples for Arduino and SDL
- [Super Gameboy and Gameboy Color](https://github.com/Mr-PauI/Walnut-CGB/tree/master#additional-resources) 24-bit RGB color databases
- Frame skip and interlacing modes (useful for slow LCDs or MCUs)
- LCD and sound can be disabled at compile time.
- If sound is enabled, an external audio processing unit (APU) library is
  required.
  A fast audio processing unit (APU) library is included in this repository at
  [https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/sdl2/minigb_apu](https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/sdl2/minigb_apu) .

## Migrating from Peanut-GB

Walnut-CGB is mostly a drop-in replacement for Peanut-GB. There are minor API differences documented [here](https://github.com/Mr-PauI/Walnut-CGB/wiki/Migrating-from-Peanut%E2%80%90GB).
  
The [wiki](https://github.com/Mr-PauI/Walnut-CGB/wiki) contains further details on implementation specifics, execution models, and framebuffer handling. Several code examples have been added to this section and I will continue to expand it.  

## Caveats

- The original 8-bit implementation is preserved, failing to use gb_run_frame_dualfetch() and disabling 16 or 32-bit dma options results is original Peanut-GB/CGB performance
- The LCD rendering is performed line by line, so certain animations will not
  render properly (such as in Prehistorik Man).
- Some games may not be playable due to emulation inaccuracy
- MiniGB APU runs in a separate thread, and so the timing is not accurate. If
  accurate APU timing and emulation is required, then Blargg's Gb_Snd_Emu
  library (or an alternative) can be used instead.

## [Arduino Example](https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/arduino/arduino.ino)

This is a basic Walnut-CGB Arduino example for the M5Stack Cardputer. 

- Paging is not included; only available RAM is used, so ROMs are extremely limited.
- Game Boy Color GIFs below were captured on a full implementation with paging.
- Internal flash storage can be used on ESP32/ESP32-S3 as long as alignment rules are observed.
- ISO C memory functions are included in comments for other platforms.

## [SDL2 Example](https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/sdl2)

The flagship example implementation is given in walnut_sdl.c, which uses SDL2 to
draw the screen and take input. Run `cmake` or `make` in the ./examples/sdl2/
folder to compile it.

Run `walnut-sdl`, which creates a *drop-zone* window that you can drag and drop
a ROM file into.  Alternatively, run in a terminal using `walnut-sdl game.gb`,
which will automatically create the save file `game.sav` for the game if one
isn't found. Or, run with `walnut-sdl game.gb save.sav` to specify a save file.

### ESP32-S3FN8 Walnut-CGB Implementation Recordings

![Mario Deluxe - Cardputer](/screencaps/MarioDeluxe_Cardputer.gif)
![Zelda: Oracle of Seasons - Cardputer](/screencaps/Zelda_OracleSeasons_Cardputer.gif)

### Screenshot 

![Pokemon Blue - Main screen animation](/screencaps/PKMN_BLUE.gif)
![Legend of Zelda: Links Awakening - animation](/screencaps/ZELDA.gif)
![Megaman V](/screencaps/MEGAMANV.png)

![Shantae](/screencaps/SHANTAE.png)
![Dragon Ball Z](/screencaps/DRAGONBALL_BBZP.png)

Note: Animated GIFs shown here are limited to 50fps, whilst the emulation was
running at the native ~60fps. This is because popular GIF decoders limit the
maximum FPS to 50.

### Controls

| Action            | Keyboard   | Joypad |
|-------------------|------------|--------|
| A                 | z          | A      |
| B                 | x          | B      |
| Start             | Return     | START  |
| Select            | Backspace  | BACK   |
| D-Pad             | Arrow Keys | DPAD   |
| Repeat A          | a          |        |
| Repeat B          | s          |        |
| Normal Speed      | 1          |        |
| Turbo x2 (Hold)   | Space      |        |
| Turbo X2 (Toggle) | 2          |        |
| Turbo X3 (Toggle) | 3          |        |
| Turbo X4 (Toggle) | 4          |        |
| Reset             | r          |        |
| Change Palette    | p          |        |
| Reset Palette     | Shift + p  |        |
| Fullscreen        | F11 / f    |        |
| Frameskip (Toggle)| o          |        |
| Interlace (Toggle)| i          |        |
| Dump BMP (Toggle) | b          |        |

Frameskip and Interlaced modes are both off by default. The Frameskip toggles
between 60 FPS and 30 FPS.

Pressing 'b' will dump each frame as a 24-bit bitmap file in the current
folder. See /screencaps/README.md for more information.

The most common functions are summarized below; further documentation of function prototypes can be found at the bottom of [walnut_cgb.h](walnut_cgb.h) and in the [wiki](https://github.com/Mr-PauI/Walnut-CGB/wiki).

### Required Functions

The front-end implementation must provide a number of functions to the library.
These functions are set when calling [gb_init](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_init()).

- [gb_rom_read](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_rom_read())
- [gb_rom_read_16bit](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_rom_read_16bit())
- [gb_rom_read_32bit](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_rom_read_32bit())
- gb_cart_ram_read
- gb_cart_ram_write
- gb_error

### Core Functions

Both of these are ways to execute cycles for one frame, and can be swapped at runtime to examine differences:  
[gb_run_frame](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_run_frame()) (original 8-bit single instruction dispatch)  
[gb_run_frame_dualfetch](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_run_frame_dualfetch()) (uses the new 16-bit dual-fetch architecture)

### Optional Features

These optional features of **Walnut-CGB** are controlled via **compile-time macros** (`#define`).  
Setting any of these macros to `1` activates the feature.

> **Note:** The current implementation of 16-bit DMA is limited to systems that do not have aliasing or alignment restrictions when writing data (e.g., ESP32-S3). On some platforms, you may need to compile with `-fno-strict-aliasing` to avoid issues with pointer aliasing. The dual-fetch chained opcode dispatch works regardless of aliasing or alignment restrictions. 32-bit DMA modes have fully alignent aware read/write options which are on by default.

| Macro | Description |
|-------|-------------|
| `WALNUT_GB_16BIT_DMA` | Enables 16-bit DMA. Only one DMA macro (16-bit or 32-bit) can be enabled at compile time. |
| `WALNUT_GB_32BIT_DMA` | Enables 32-bit DMA. Only one DMA macro (16-bit or 32-bit) can be enabled at compile time. |
| `WALNUT_GB_16BIT_ALIGNED` | If your platform cannot handle or has a severe penalty for unaligned 16-bit reads, this feature performs aligned 16-bit reads with an 8-bit fallback.|
| `WALNUT_GB_32BIT_ALIGNED` | If your platform cannot handle or has a severe penalty for unaligned 32-bit reads/writes, this feature performs aligned 32-bit reads/writes with an 8-bit fallback.|
| `WALNUT_GB_RGB565_BIGENDIAN` | If your display uses native **big-endian RGB565**, this macro switches the default little-endian RGB565 output to big-endian. |


### Optional Functions

The following optional functions may be defined for further functionality.

#### [lcd_draw_line](https://github.com/Mr-PauI/Walnut-CGB/wiki/lcd_draw_line-example-%7C-Rendering-the-frame-for-DMG-and-CGB)

This function is required for LCD drawing. Set this function using gb_init_lcd
and enable LCD functionality within Walnut-CGB by defining ENABLE_LCD to 1 before
including walnut_cgb.h. ENABLE_LCD is set to 1 by default if it was not
previously defined. If gb_init_lcd is not called or lcd_draw_line is set to
NULL, then LCD drawing is disabled.

If running a gameboy colour(CGB) game, the pixel data sent to lcd_draw_line contains
indexes to the current palette. 
If running a gameboy(DMG) game the pixel data sent to lcd_draw_line comes with both shade and layer data. The
first two least significant bits are the shade data (black, dark, light, white).
Bits 4 and 5 are layer data (OBJ0, OBJ1, BG), which can be used to add more
colours to the game in the same way that the Game Boy Color does to older Game
Boy games.

#### audio_read and audio_write

These functions are required for audio emulation and output. Walnut-CGB does not
include audio emulation, so an external library must be used. These functions
must be defined and audio output must be enabled by defining ENABLE_SOUND to 1
before including walnut_cgb.h. 

#### gb_serial_tx and gb_serial_rx

These functions are required for serial communication. Set these functions using
gb_init_serial. If these functions are not set, then the emulation will act as
though no link cable is connected.

### Useful Functions

These functions are provided by Walnut-CGB.

#### [gb_reset](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_reset())

This function resets the game being played, as though the console had been
powered off and on. gb_reset is called by [gb_init](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_init()) to initialise the CPU
registers.

#### [gb_get_save_size](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_get_save_size_s())

This function returns the save size of the game being played. This function
returns 0 if the game does not use any save data.

#### [gb_run_frame_dualfetch](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_run_frame_dualfetch())

This function runs the CPU until a full frame is rendered to the LCD using the faster dual-fetch chained opcode dispatch.
This is the default function to use when using Walnut-CGB. 

#### [gb_run_frame](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_run_frame())

This function runs the CPU until a full frame is rendered to the LCD using the original 8-bit single opcode dispatch.

#### [gb_colour_hash](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_colour_hash())

This function calculates a hash of the game title. This hash is calculated in
the same way as the Game Boy Color to add colour to Game Boy games.

#### [gb_get_rom_name](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_get_rom_name())

This function returns the name of the game.

#### [gb_set_rtc](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_set_rtc())

Set the time of the real time clock (RTC). Some games use this RTC data.

#### gb_tick_rtc

Deprecated: do not use. The RTC is ticked internally.

#### [gb_set_bootrom](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_set_bootrom())

Execute a bootrom image on reset. A reset must be performed after calling
gb_set_bootrom for these changes to take effect. This is because [gb_init](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_init()) calls
[gb_reset](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_reset()), but gb_set_bootrom must be called after [gb_init](https://github.com/Mr-PauI/Walnut-CGB/wiki/gb_init()).
The bootrom must be either a CGB, DMG or a MGB bootrom.


### Additional Resources

For developers interested in implementing automatic color matching, I’ve included some ready-to-use palette data:

- **Super Game Boy Palettes** – Indexed 24-bit RGB888 format, includes approximations of official and community-sourced palettes. Found in [`extras/sgb.h`](https://github.com/Mr-PauI/Walnut-CGB/blob/master/extras/sgb.h)
- **Game Boy Color Palettes** – Indexed 24-bit RGB888 format, aproximation of official palettes only. Found in [`extras/cgb.h`](https://github.com/Mr-PauI/Walnut-CGB/blob/master/extras/cgb.h)

These arrays can be used directly in your projects for accurate color reproduction. See the wiki for [implementation details](https://github.com/Mr-PauI/Walnut-CGB/wiki/Using-the-color-databases).

![Super Gameboy Palette Resource](https://github.com/Mr-PauI/Walnut-CGB/blob/master/screencaps/sgb_example.png)  
*Example of sgb.h palettes matched with popular titles*


For developers interested in adding sound to their implementation, the following library is included in the SDL2 example directory:
[https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/sdl2/minigb_apu](https://github.com/Mr-PauI/Walnut-CGB/tree/master/examples/sdl2/minigb_apu)

## License

This project is licensed under the MIT License.
