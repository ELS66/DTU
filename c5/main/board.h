#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#define BOARD_FIELD_TX 23
#define BOARD_FIELD_RX 24
#define BOARD_RS485_DE 3
#define BOARD_LTE_TX 0
#define BOARD_LTE_RX 1
#define BOARD_LTE_PWRKEY 6
#define BOARD_LTE_RESET 8
esp_err_t board_init(void);
/* Sole runtime caller: indicator task. Bits are logical ON; hardware is active low. */
void board_apply_led_mask(uint8_t on_mask);
