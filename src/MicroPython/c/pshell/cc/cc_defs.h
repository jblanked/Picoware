// clang-format off
static const struct define_grp stdio_defines[] = {
    // OPEN
    {"TRUE", 1},
    {"true", 1},
    {"FALSE", 0},
    {"false", 0},
    {"O_RDONLY", O_RDONLY},
    {"O_WRONLY", O_WRONLY},
    {"O_RDWR", O_RDWR},
    {"O_CREAT", O_CREAT},                       // Create a file if it does not exist
    {"O_EXCL", O_EXCL},                         // Fail if a file already exists
    {"O_TRUNC", O_TRUNC},                       // Truncate the existing file to zero size
    {"O_APPEND", O_APPEND},                     // Move to end of file on every write
    {"SEEK_SET", LFS_SEEK_SET},                 //
    {"SEEK_CUR", LFS_SEEK_CUR},                 //
    {"SEEK_END", LFS_SEEK_END},                 //
    {"PICO_ERROR_TIMEOUT", PICO_ERROR_TIMEOUT}, //
    {0}};

static const struct define_grp gpio_defines[] = {
    // GPIO
#if PICO_RM2040
    {"GPIO_FUNC_XIP", GPIO_FUNC_XIP},
    {"GPIO_IO_IRQ_LEVEL_LOW", GPIO_IO_IRQ_LEVEL_LOW},
    {"GPIO_IRQ_LEVEL_HIGH", GPIO_IRQ_LEVEL_HIGH},
    {"GPIO_IRQ_EDGE_FALL", GPIO_IRQ_EDGE_FALL},
    {"GPIO_IRQ_EDGE_RISE", GPIO_IRQ_EDGE_RISE},
#endif
#if PICO_RM2350
    {"GPIO_FUNC_HSTX", GPIO_FUNC_HSTX},
    {"GPIO_FUNC_PIO2", GPIO_FUNC_PIO2},
#endif
    {"GPIO_FUNC_SPI", GPIO_FUNC_SPI},
    {"GPIO_FUNC_UART", GPIO_FUNC_UART},
    {"GPIO_FUNC_I2C", GPIO_FUNC_I2C},
    {"GPIO_FUNC_PWM", GPIO_FUNC_PWM},
    {"GPIO_FUNC_SIO", GPIO_FUNC_SIO},
#if PICO_RP2040
    {"GPIO_FUNC_PIO0", GPIO_FUNC_PIO0},
    {"GPIO_FUNC_PIO1", GPIO_FUNC_PIO1},
#endif
#if PICO_RP2350
    {"PROC0_IRQ_CTI", PROC0_IRQ_CTI},
    {"PROC1_IRQ_CTI", PROC1_IRQ_CTI},
#endif
    {"GPIO_FUNC_GPCK", GPIO_FUNC_GPCK},
#if PICO_RM2350
    {"GPIO_FUNC_XIP_CS1", GPIO_FUNC_XIP_CS1},
    {"GPIO_FUNC_CORESIGHT_TRACE", GPIO_FUNC_CORESIGHT_TRACE},
#endif
    {"GPIO_FUNC_USB", GPIO_FUNC_USB},
#if PICO_RM2350
    {"GPIO_FUNC_UART_AUX", GPIO_FUNC_UART_AUX},
#endif
    {"GPIO_FUNC_NULL", GPIO_FUNC_NULL},
    {"GPIO_OUT", GPIO_OUT},
    {"GPIO_IN", GPIO_IN},
    {"GPIO_IRQ_LEVEL_LOW", GPIO_IRQ_LEVEL_LOW},
    {"GPIO_IRQ_LEVEL_HIGH", GPIO_IRQ_LEVEL_HIGH},
    {"GPIO_IRQ_EDGE_FALL", GPIO_IRQ_EDGE_FALL},
    {"GPIO_IRQ_EDGE_RISE", GPIO_IRQ_EDGE_RISE},
    {"GPIO_SLEW_RATE_SLOW", GPIO_SLEW_RATE_SLOW},
    {"GPIO_SLEW_RATE_FAST", GPIO_SLEW_RATE_FAST},
    {"GPIO_DRIVE_STRENGTH_2MA", GPIO_DRIVE_STRENGTH_2MA},
    {"GPIO_DRIVE_STRENGTH_4MA", GPIO_DRIVE_STRENGTH_4MA},
    {"GPIO_DRIVE_STRENGTH_8MA", GPIO_DRIVE_STRENGTH_8MA},
    {"GPIO_DRIVE_STRENGTH_12MA", GPIO_DRIVE_STRENGTH_12MA},

#if defined(PICO_DEFAULT_LED_PIN)
    // LED
    {"PICO_DEFAULT_LED_PIN", PICO_DEFAULT_LED_PIN},
#endif
    {0}};

static const struct define_grp pwm_defines[] = {
    // PWM
    {"PWM_DIV_FREE_RUNNING", PWM_DIV_FREE_RUNNING},
    {"PWM_DIV_B_HIGH", PWM_DIV_B_HIGH},
    {"PWM_DIV_B_RISING", PWM_DIV_B_RISING},
    {"PWM_DIV_B_FALLING", PWM_DIV_B_FALLING},
    {"PWM_CHAN_A", PWM_CHAN_A},
    {"PWM_CHAN_B", PWM_CHAN_B},
    {0}};

static const struct define_grp clk_defines[] = {
    // CLOCKS
    {"KHZ", KHZ},
    {"MHZ", MHZ},
    {"clk_gpout0", clk_gpout0},
    {"clk_gpout1", clk_gpout1},
    {"clk_gpout2", clk_gpout2},
    {"clk_gpout3", clk_gpout3},
    {"clk_ref", clk_ref},
    {"clk_sys", clk_sys},
    {"clk_peri", clk_peri},
    {"clk_usb", clk_usb},
    {"clk_adc", clk_adc},
#if PICO_RP2040
    {"clk_rtc", clk_rtc},
#endif
    {"CLK_COUNT", CLK_COUNT},
    {0}};

static const struct define_grp i2c_defines[] = {
    // I2C
    {"i2c0", (int)&i2c0_inst},
    {"i2c1", (int)&i2c1_inst},
#if PICO_SDK_VERSION_MAJOR < 2
    {"i2c_default", (int)PICO_DEFAULT_I2C_INSTANCE},
#endif
    {0}};

static const struct define_grp spi_defines[] = {
    // SPI
    {"spi0", (int)spi0_hw},
    {"spi1", (int)spi1_hw},
#if PICO_SDK_VERSION_MAJOR < 2
    {"spi_default", (int)PICO_DEFAULT_SPI_INSTANCE},
#endif
    {0}};

static const struct define_grp math_defines[] = {{0}};

static const struct define_grp adc_defines[] = {{0}};

static const struct define_grp stdlib_defines[] = {{0}};

static const struct define_grp string_defines[] = {{0}};

static const struct define_grp time_defines[] = {{0}};

static const struct define_grp sync_defines[] = {{0}};

static const struct define_grp irq_defines[] = {
    // IRQ
#if PICO_RP2040
    {"TIMER_IRQ_0", TIMER_IRQ_0},
    {"TIMER_IRQ_1", TIMER_IRQ_1},
    {"TIMER_IRQ_2", TIMER_IRQ_2},
    {"TIMER_IRQ_3", TIMER_IRQ_3},
#endif
#if PICO_RP2350
    {"TIMER0_IRQ_0", TIMER0_IRQ_0},
    {"TIMER0_IRQ_1", TIMER0_IRQ_1},
    {"TIMER0_IRQ_2", TIMER0_IRQ_2},
    {"TIMER0_IRQ_3", TIMER0_IRQ_3},
    {"TIMER1_IRQ_0", TIMER1_IRQ_0},
    {"TIMER1_IRQ_1", TIMER1_IRQ_1},
    {"TIMER1_IRQ_2", TIMER1_IRQ_2},
    {"TIMER1_IRQ_3", TIMER1_IRQ_3},
    {"PWM_IRQ_WRAP_0", PWM_IRQ_WRAP_0},
    {"PWM_IRQ_WRAP_1", PWM_IRQ_WRAP_1},
#endif
    {"PWM_IRQ_WRAP", PWM_IRQ_WRAP},
    {"USBCTRL_IRQ", USBCTRL_IRQ},
#if PICO_RP2040
    {"XIP_IRQ", XIP_IRQ},
#endif
    {"PIO0_IRQ_0", PIO0_IRQ_0},
    {"PIO0_IRQ_1", PIO0_IRQ_1},
    {"PIO1_IRQ_0", PIO1_IRQ_0},
    {"PIO1_IRQ_1", PIO1_IRQ_1},
    {"DMA_IRQ_0", DMA_IRQ_0},
    {"DMA_IRQ_1", DMA_IRQ_1},
    {"IO_IRQ_BANK0", IO_IRQ_BANK0},
    {"IO_IRQ_QSPI", IO_IRQ_QSPI},
    {"CLOCKS_IRQ", CLOCKS_IRQ},
    {"SPI0_IRQ", SPI0_IRQ},
    {"SPI1_IRQ", SPI1_IRQ},
    {"UART0_IRQ", UART0_IRQ},
    {"UART1_IRQ", UART1_IRQ},
    {"ADC_IRQ_FIFO", ADC_IRQ_FIFO},
    {"I2C0_IRQ", I2C0_IRQ},
    {"I2C1_IRQ", I2C1_IRQ},
#if PICO_RP2040
    {"RTC_IRQ", RTC_IRQ},
#endif
    {"PICO_DEFAULT_IRQ_PRIORITY", PICO_DEFAULT_IRQ_PRIORITY},
    {"PICO_LOWEST_IRQ_PRIORITY", PICO_LOWEST_IRQ_PRIORITY},
    {"PICO_HIGHEST_IRQ_PRIORITY", PICO_HIGHEST_IRQ_PRIORITY},
    {"PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY",
     PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY},
    {"PICO_SHARED_IRQ_HANDLER_HIGHEST_ORDER_PRIORITY",
     PICO_SHARED_IRQ_HANDLER_HIGHEST_ORDER_PRIORITY},
    {"PICO_SHARED_IRQ_HANDLER_LOWEST_ORDER_PRIORITY",
     PICO_SHARED_IRQ_HANDLER_LOWEST_ORDER_PRIORITY},
    {0}};

static const struct define_grp uart_defines[] = {
    // UART
    {"UART_PARITY_NONE", UART_PARITY_NONE},
    {"UART_PARITY_EVEN", UART_PARITY_EVEN},
    {"UART_PARITY_ODD", UART_PARITY_ODD},
    {"uart0", ((uint32_t)uart0_hw)},
    {"uart1", ((uint32_t)uart1_hw)},
    {0}};
// clang-format on
