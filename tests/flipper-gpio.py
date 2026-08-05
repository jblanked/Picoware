from machine import Pin
from utime import sleep_ms

# ============================================================================
# Flipper Zero — full GPIO reference
# ref: https://docs.flipper.net/zero/gpio-and-modules#gpio-pinout
# Board aliases come from src/MicroPython/Flipper/board/pins.csv.
# Raw CPU pins are exposed as Pin.cpu.<letter><number>, e.g. Pin.cpu.A7.
#
#   Right column (1-8)        Left column (9-18)
#   1  5V                     9  3V3
#   2  PA7                   10  PA14   (SWD_CLK, debug)
#   3  PA6                   11  GND
#   4  PA4                   12  PA13   (SWD_IO, debug)
#   5  PB3                   13  PB6    (USART1_TX, debug)
#   6  PB2                   14  PB7    (USART1_RX, debug)
#   7  PC3                   15  PC1
#   8  GND                   16  PC0
#                             17  PB14   (iButton, debug)
#                             18  GND
# ============================================================================

# power rails 
FLIPPER_PIN_5V = 1          # pin 1, fused, up to 1.2A (enable: GPIO app -> 5V on GPIO)
FLIPPER_PIN_3V3 = 9         # pin 9, up to 1.2A (disabled during SD mount / updates)
FLIPPER_PIN_GND_8 = 8       # pin 8 ground
FLIPPER_PIN_GND_11 = 11     # pin 11 ground
FLIPPER_PIN_GND_18 = 18     # pin 18 ground

# right column, pins 2-7 (safe to drive)
FLIPPER_PIN_2_PA7 = Pin.cpu.A7   # SPI1_MOSI / ADC1_12 / TIM1_CH1N
FLIPPER_PIN_3_PA6 = Pin.cpu.A6   # SPI1_MISO / ADC1_11 / TIM1_BKIN
FLIPPER_PIN_4_PA4 = Pin.cpu.A4   # SPI1_NSS  / ADC1_9  / LPTIM2_OUT
FLIPPER_PIN_5_PB3 = Pin.cpu.B3   # SPI1_SCK  / USART1_DE / SWO
FLIPPER_PIN_6_PB2 = Pin.cpu.B2   # SPI1_NSS  / NFC (shared)
FLIPPER_PIN_7_PC3 = Pin.cpu.C3   # ADC1_4    / LPTIM1_ETR / LPTIM2_ETR

# left column, pins 10-17
FLIPPER_PIN_10_PA14 = Pin.cpu.A14  # SWD_CLK (debug header)
FLIPPER_PIN_12_PA13 = Pin.cpu.A13  # SWD_IO  (debug header), back key
FLIPPER_PIN_13_PB6 = Pin.cpu.B6    # USART1_TX (debug UART)
FLIPPER_PIN_14_PB7 = Pin.cpu.B7    # USART1_RX (debug UART)
FLIPPER_PIN_15_PC1 = Pin.cpu.C1    # LPUART1_TX / ADC1_2 / I2C3_SDA (SubGHz shared)
FLIPPER_PIN_16_PC0 = Pin.cpu.C0    # LPUART1_RX / ADC1_1 / I2C3_SCL
FLIPPER_PIN_17_PB14 = Pin.cpu.B14  # iButton 1-wire, 5V pull-up (debug header)

# dangerous pins (stock firmware marks these; can damage hardware)
FLIPPER_PIN_DANGER_PB8 = Pin.cpu.B8  # speaker (PWM)
FLIPPER_PIN_DANGER_PB9 = Pin.cpu.B9  # IR TX LED

# dpad / buttons 
FLIPPER_PIN_BACK = Pin.board.BTN_BACK   # PC13
FLIPPER_PIN_DOWN = Pin.board.BTN_DOWN   # PC6
FLIPPER_PIN_LEFT = Pin.board.BTN_LEFT   # PB11
FLIPPER_PIN_OK = Pin.board.BTN_OK       # PH3
FLIPPER_PIN_RIGHT = Pin.board.BTN_RIGHT # PB12
FLIPPER_PIN_UP = Pin.board.BTN_UP       # PB10

# vibration motor / MCO 
FLIPPER_PIN_LED = Pin.board.LED   # PA8 -- actually the vibration motor, not an LED
FLIPPER_PIN_VIBRO = Pin.board.LED # PA8 -- also the MCO clock output

# RGB LED + backlight (LP5562 I2C LED driver @ 0x60 on I2C1)
# Backlight: lcd.set_brightness(0-100)
# RGB LED:   lcd.set_rgb_led(r, g, b) with 0-255 per channel
FLIPPER_PIN_I2C1_SCL = Pin.cpu.A9
FLIPPER_PIN_I2C1_SDA = Pin.cpu.A10
FLIPPER_LP5562_ADDR = 0x60

# SD card 
FLIPPER_PIN_SD_CD = Pin.board.SD_CD   # PC10 (card detect, active low)
FLIPPER_PIN_SD_CS = Pin.board.SD_CS   # PC12

# display SPI (SPI2)
FLIPPER_PIN_SPI2_MISO = Pin.board.SPI2_MISO  # PC2
FLIPPER_PIN_SPI2_MOSI = Pin.board.SPI2_MOSI  # PB15
FLIPPER_PIN_SPI2_NSS = Pin.board.SPI2_NSS    # PC11 (display CS)
FLIPPER_PIN_SPI2_SCK = Pin.board.SPI2_SCK    # PD1

# USB
FLIPPER_PIN_USB_DM = Pin.board.USB_DM  # PA11
FLIPPER_PIN_USB_DP = Pin.board.USB_DP  # PA12

# misc internal
FLIPPER_PIN_PERIPH_POWER = Pin.cpu.A3  # PA3 -- 3V3 rail enable (open-drain), drives SD + display power


# GPIO test
p = Pin(FLIPPER_PIN_15_PC1, Pin.OUT)

p.on()
sleep_ms(500)
p.off()


# led test
from picoware.gui.draw import Draw

lcd = Draw()

lcd.set_rgb_led(255, 0, 0)  # red
sleep_ms(500)
lcd.set_rgb_led(0, 255, 0)  # green
sleep_ms(500)
lcd.set_rgb_led(0, 0, 255)  # blue
sleep_ms(500)
lcd.set_rgb_led(255, 255, 255)  # white
sleep_ms(500)
lcd.set_rgb_led(0, 0, 0)  # off

del lcd
lcd = None