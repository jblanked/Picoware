// source https://github.com/lewisxhe/XPowersLib/blob/master/src/REG/AXP2101Constants.h

#pragma once

#ifdef _BV
#undef _BV
#endif
#define _BV(b)                          (1ULL << (uint64_t)(b))

#define XPOWERS_AXP2101_STATUS1                          (0x00)
#define XPOWERS_AXP2101_STATUS2                          (0x01)

#define XPOWERS_AXP2101_ADC_CHANNEL_CTRL                 (0x30)
#define XPOWERS_AXP2101_ADC_DATA_RELUST0                 (0x34)
#define XPOWERS_AXP2101_ADC_DATA_RELUST1                 (0x35)

//XPOWERS INTERRUPT STATUS REGISTER
#define XPOWERS_AXP2101_INTSTS1                          (0x48)
#define XPOWERS_AXP2101_INTSTS2                          (0x49)
#define XPOWERS_AXP2101_INTSTS3                          (0x4A)
#define XPOWERS_AXP2101_INTSTS_CNT                       (3)

#define XPOWERS_AXP2101_BAT_PERCENT_DATA                 (0xA4)
