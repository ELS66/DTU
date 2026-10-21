idf_component_register(
    SRCS "app_main.c" "board.c" "field_bus.c" "runtime_store.c" "diagnostics.c" "modem.c" "network.c" "uplink.c" "indicators.c" "supervision.c" "board_cache.c" "event_log.c"
    INCLUDE_DIRS "."
    REQUIRES module_core esp_driver_gpio esp_driver_uart esp_timer esp_psram
             esp_system esp_hw_support esp_app_format spi_flash nvs_flash console esp_wifi esp_event esp_netif lwip)
