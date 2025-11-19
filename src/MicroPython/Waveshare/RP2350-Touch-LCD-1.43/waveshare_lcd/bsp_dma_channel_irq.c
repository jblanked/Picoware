#include "bsp_dma_channel_irq.h"
#include "hardware/irq.h"
#include "hardware/dma.h"

typedef struct
{
    channel_irq_callback_t callback[13];
    uint dma_channel[13];
    uint16_t len;
    bool is_init;
} bsp_channel_irq_info_t;

bsp_channel_irq_info_t g_irq1_info = {
    .len = 0,
    .is_init = false};

void dma_iqr1_handler(void)
{
    for (int i = 0; i < g_irq1_info.len; i++)
    {
        if (dma_channel_get_irq1_status(g_irq1_info.dma_channel[i]))
        {
            dma_channel_acknowledge_irq1(g_irq1_info.dma_channel[i]);
            g_irq1_info.callback[i]();
        }
    }
}

void bsp_dma_channel_irq_add(uint8_t irq_num, uint dma_channel, channel_irq_callback_t callback)
{
    if (NULL == callback)
    {
        printf("callback is NULL!\r\n");
        return;
    }

    if (1 == irq_num)
    {
        dma_channel_set_irq1_enabled(dma_channel, true);
        g_irq1_info.dma_channel[g_irq1_info.len] = dma_channel;
        g_irq1_info.callback[g_irq1_info.len] = callback;
        g_irq1_info.len++;
        if (g_irq1_info.is_init == false)
        {
            bsp_dma_channel_irq1_init();
        }
    }
}

void bsp_dma_channel_irq1_init(void)
{
    // g_irq1_info.len = 0;
    g_irq1_info.is_init = true;
    // Tell the DMA to raise IRQ line 0 when the channel finishes a block
    // dma_channel_set_irq0_enabled(dma_chan, true);

    // Configure the processor to run dma_handler() when DMA IRQ 0 is asserted
    irq_set_exclusive_handler(DMA_IRQ_1, dma_iqr1_handler);
    irq_set_enabled(DMA_IRQ_1, true);
}
