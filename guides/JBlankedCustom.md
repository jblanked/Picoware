## About
A custom Raspberry Pi Pico setup.

## Materials
- Raspberry Pi Pico (any variant)
- 2.4-inch SPI TFT LCD Display ILI9341 Touch Panel 240x320
- HW504 joystick (optional)
- Push button switches

## TFT to Pico Wiring
- VCC -> VSYS (Pin 39)
- GND -> GND
- CS -> GP5 (Pin 7)
- RESET -> GP10 (Pin 14)
- DC -> GP11 (Pin 15)
- SDI/MOSI -> GP7 (Pin 10)
- SCK -> GP6 (Pin 9)
- LED -> VSYS (Pin 39)
- SDO/MISO -> GP4 (Pin 6)
- SD_SCK -> GP14 (Pin 19)
- SD_MISO -> GP12 (Pin 16)
- SD_MOSI -> GP15 (Pin 20)
- SD_CS -> GP13 (Pin 17)

## HW504 to Pico Wiring
- SW -> GP17 (Pin 22 - TX)
- VRx -> GP27 (Pin 32 - ADC1)
- VRy -> GP26 (Pin 31 - ADC0)
- GND -> GND
- 5V -> VSYS (Pin 39)

## Button Mapping (Pico) Wiring
- GP16 (Pin 21) -> UP
- GP17 (Pin 22) -> RIGHT
- GP18 (Pin 24) -> DOWN
- GP19 (Pin 25) -> LEFT