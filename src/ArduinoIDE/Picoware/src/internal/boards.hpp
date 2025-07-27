#pragma once
#include <Arduino.h>

namespace Picoware
{
    typedef enum
    {
        BOARD_TYPE_PICO_CALC = 0,
        BOARD_TYPE_VGM = 1,
        BOARD_TYPE_JBLANKED = 2,
    } BoardType;

    typedef enum
    {
        PICO_TYPE_PICO = 0,    // Raspberry Pi Pico
        PICO_TYPE_PICO_W = 1,  // Raspberry Pi Pico W
        PICO_TYPE_PICO_2 = 2,  // Raspberry Pi Pico 2
        PICO_TYPE_PICO_2_W = 3 // Raspberry Pi Pico 2 W
    } PicoType;

    typedef enum
    {
        LIBRARY_TYPE_PICO_DVI = 0,
        LIBRARY_TYPE_TFT = 1
    } LibraryType;

    typedef struct
    {
        uint8_t sck;
        uint8_t mosi;
        uint8_t miso;
        uint8_t cs;
        uint8_t dc;
        uint8_t rst;
    } BoardPins;

    typedef struct
    {
        BoardType boardType;
        PicoType picoType;
        LibraryType libraryType;
        BoardPins pins;
        uint16_t width;
        uint16_t height;
        uint8_t rotation;
        const char *name;
        bool hasWiFi;
        bool hasBluetooth;
        bool hasSDCard;
        bool hasBattery;
    } Board;

    static const PROGMEM Board VGMConfig = {
        .boardType = BOARD_TYPE_VGM,
        .picoType = PICO_TYPE_PICO,
        .libraryType = LIBRARY_TYPE_PICO_DVI,
        .pins = {
            .sck = 8,
            .mosi = 11,
            .miso = 12,
            .cs = 13,
            .dc = 14,
            .rst = 15},
        .width = 320,
        .height = 240,
        .rotation = 0,
        .name = "Video Game Module",
        .hasWiFi = false,
        .hasBluetooth = false,
        .hasSDCard = false,
        .hasBattery = false};

    static const PROGMEM Board PicoCalcConfigPico = {
        .boardType = BOARD_TYPE_PICO_CALC,
        .picoType = PICO_TYPE_PICO,
        .libraryType = LIBRARY_TYPE_TFT,
        .pins = {
            .sck = 10,
            .mosi = 11,
            .miso = 12,
            .cs = 13,
            .dc = 14,
            .rst = 15},
        .width = 320,
        .height = 320,
        .rotation = 0,
        .name = "PicoCalc - Pico",
        .hasWiFi = false,
        .hasBluetooth = false,
        .hasSDCard = true,
        .hasBattery = true};

    static const PROGMEM Board PicoCalcConfigPicoW = {
        .boardType = BOARD_TYPE_PICO_CALC,
        .picoType = PICO_TYPE_PICO_W,
        .libraryType = LIBRARY_TYPE_TFT,
        .pins = {
            .sck = 10,
            .mosi = 11,
            .miso = 12,
            .cs = 13,
            .dc = 14,
            .rst = 15},
        .width = 320,
        .height = 320,
        .rotation = 0,
        .name = "PicoCalc - Pico W",
        .hasWiFi = true,
        .hasBluetooth = true,
        .hasSDCard = true,
        .hasBattery = true};

    static const PROGMEM Board PicoCalcConfigPico2 = {
        .boardType = BOARD_TYPE_PICO_CALC,
        .picoType = PICO_TYPE_PICO_2,
        .libraryType = LIBRARY_TYPE_TFT,
        .pins = {
            .sck = 10,
            .mosi = 11,
            .miso = 12,
            .cs = 13,
            .dc = 14,
            .rst = 15},
        .width = 320,
        .height = 320,
        .rotation = 0,
        .name = "PicoCalc - Pico 2",
        .hasWiFi = false,
        .hasBluetooth = false,
        .hasSDCard = true,
        .hasBattery = true};

    static const PROGMEM Board PicoCalcConfigPico2W = {
        .boardType = BOARD_TYPE_PICO_CALC,
        .picoType = PICO_TYPE_PICO_2_W,
        .libraryType = LIBRARY_TYPE_TFT,
        .pins = {
            .sck = 10,
            .mosi = 11,
            .miso = 12,
            .cs = 13,
            .dc = 14,
            .rst = 15},
        .width = 320,
        .height = 320,
        .rotation = 0,
        .name = "PicoCalc - Pico 2 W",
        .hasWiFi = true,
        .hasBluetooth = true,
        .hasSDCard = true,
        .hasBattery = true};

    static const PROGMEM Board JBlankedPicoConfig = {
        .boardType = BOARD_TYPE_JBLANKED,
        .picoType = PICO_TYPE_PICO_W,
        .libraryType = LIBRARY_TYPE_TFT,
        .pins = {
            .sck = 6,
            .mosi = 7,
            .miso = 4,
            .cs = 5,
            .dc = 11,
            .rst = 10},
        .width = 320,
        .height = 240,
        .rotation = 3,
        .name = "JBlanked Pico",
        .hasWiFi = true,
        .hasBluetooth = true,
        .hasSDCard = false,
        .hasBattery = false};

} // namespace Picoware