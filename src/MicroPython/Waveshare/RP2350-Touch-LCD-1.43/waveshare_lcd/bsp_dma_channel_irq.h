#ifndef __BSP_DMA_CHANNEL_IRQ_H__
#define __BSP_DMA_CHANNEL_IRQ_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pico/stdlib.h"

typedef void (*channel_irq_callback_t)(void);



void bsp_dma_channel_irq1_init(void);
void bsp_dma_channel_irq_add(uint8_t irq_num, uint dma_channel, channel_irq_callback_t callback);

#endif // __BSP_DMA_CHANNEL_IRQ_H__

