#include "board.h"
#include "driver/gpio.h"
#include "module_indicator.h"
static const gpio_num_t leds[] = {2, 4, 5, 7, 9, 25, 11, 12};
_Static_assert(sizeof(leds) / sizeof(leds[0]) == MODULE_LED_COUNT, "LED mapping size");
esp_err_t board_init(void)
{
    uint64_t mask = 0;
    for (unsigned i = 0; i < sizeof(leds) / sizeof(leds[0]); ++i) {
        gpio_set_level(leds[i], 1);
        mask |= UINT64_C(1) << leds[i];
    }
    gpio_set_level(BOARD_RS485_DE, 0);
    gpio_set_level(BOARD_LTE_PWRKEY, 0);
    gpio_set_level(BOARD_LTE_RESET, 0);
    mask |= (UINT64_C(1) << BOARD_RS485_DE) | (UINT64_C(1) << BOARD_LTE_PWRKEY) |
            (UINT64_C(1) << BOARD_LTE_RESET);
    gpio_config_t config = {.pin_bit_mask = mask, .mode = GPIO_MODE_OUTPUT};
    return gpio_config(&config);
}
void board_apply_led_mask(uint8_t on_mask)
{
    for (unsigned i = 0; i < MODULE_LED_COUNT; ++i)
        gpio_set_level(leds[i], (on_mask & (1u << i)) ? 0 : 1);
}
