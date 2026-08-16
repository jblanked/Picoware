# MMBasic Guide

[MMBasic](https://geoffg.net/micromite-mmbasic.html) is a BASIC interpreter originally written for the Micromite/Maximite microcontroller boards by Geoff Graham. Picoware includes a port of MMBasic so you can run `.bas` programs directly on your device.

## What is MMBasic?

MMBasic is a full-featured BASIC dialect designed for microcontrollers. Programs use a simple line-oriented syntax with `PRINT`, `FOR`/`NEXT`, `IF`/`THEN`, `SUB`/`END SUB`, `DO`/`LOOP`, and graphics commands such as `LINE`, `CIRCLE`, `BOX`, and `TEXT`. Picoware's port is based on MMBasic 6.03 and runs a good portion of existing MMBasic programs, including many written for the PicoCalc.

## Adding programs

Copy `.bas` files to the `picoware/mmbasic` folder on your SD card:

```
picoware/
  mmbasic/
    clock.bas
    mygame.bas
```

Each file appears in the MMBasic app menu (the `.bas` extension is hidden). There is no need to compile anything; the source is loaded and interpreted when you select it.

## Running a program

1. Open the **MMBasic** app from the launcher.
2. Use the arrow keys (up/down/left/right) to scroll through the program list.
3. Press the center button to run the selected program.
4. Press **BACK** to stop the program and return to the menu.

Programs that end with `END` or `STOP` keep their final screen on display; press **BACK** to return to the menu. `INPUT` (and `LINE INPUT`) reads text from the keyboard, and the center button acts as Enter.

## Example

Save the following as `picoware/mmbasic/hello.bas`:

```basic
CLS
PRINT "Hello from MMBasic!"
PRINT
INPUT "What is your name? ", name$
PRINT "Hi, " + name$
END
```

Graphics programs use the device screen directly. For example:

```basic
CLS
COLOR RGB(white)
BOX 10,10,100,100,,,RGB(red),RGB(red)
TEXT 160,160,"Picoware",cm
END
```

## Notes

- Programs that use many per-pixel graphics operations can be slow; the interpreter is not the bottleneck, the drawing is.
- MMBasic on Picoware is a port of the standard dialect, so most programs written for the PicoCalc or other MMBasic devices should run as-is. Advanced features that depend on specific hardware may not be available.
- For developers, the interpreter core lives in `src/MicroPython/mmbasic/`, and the host app wrapper is `picoware/system/mmbasic.py`.
