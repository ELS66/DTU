#pragma once
#include <stdbool.h>
#include <stdint.h>
#define MODULE_WATCH_COUNT 5u
typedef enum { MODULE_WATCH_FIELD, MODULE_WATCH_STORE, MODULE_WATCH_LED,
               MODULE_WATCH_NETWORK, MODULE_WATCH_MODEM } module_watch_id_t;
typedef struct {
    bool enabled;
    uint32_t budget_ms, advances;
    uint64_t last_progress_ms;
} module_watch_slot_t;
typedef struct {
    module_watch_slot_t slots[MODULE_WATCH_COUNT];
    uint32_t fault_mask;
    uint64_t fault_ms;
} module_watch_t;
bool module_watch_enable(module_watch_t *watch, unsigned id, uint32_t budget_ms, uint64_t now);
void module_watch_disable(module_watch_t *watch, unsigned id);
bool module_watch_progress(module_watch_t *watch, unsigned id, uint64_t now);
/* A detected stall is latched until reboot; later progress cannot hide it. */
uint32_t module_watch_evaluate(module_watch_t *watch, uint64_t now);

enum {
    MODULE_UART_FIFO = 1u, MODULE_UART_BUFFER = 2u, MODULE_UART_FRAME = 4u,
    MODULE_UART_PARITY = 8u, MODULE_UART_BREAK = 16u, MODULE_UART_QUEUE_FULL = 32u,
    MODULE_UART_READ = 64u
};
typedef struct {
    uint32_t fault_batches, consecutive_faults, recoveries;
    uint32_t fifo, buffer, frame, parity, breaks, queue_full, read_errors;
    uint32_t pressure_batches, queue_peak, last_flags;
    bool recovering;
    uint64_t last_fault_ms, guard_until_ms;
} module_uart_health_t;
/* Queue occupancy is a sampled high-water mark, not an exact driver-drop counter. */
bool module_uart_pressure(module_uart_health_t *health, unsigned queued, unsigned capacity);
void module_uart_fault(module_uart_health_t *health, uint32_t flags, uint64_t now, uint32_t guard_ms);
bool module_uart_good(module_uart_health_t *health, uint64_t now);
