#ifndef MODULE_AT_H
#define MODULE_AT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "network_policy.h"
#define MODULE_AT_LINE_MAX 832
typedef void (*module_at_line_fn)(void *context, const char *line);
typedef enum { MODULE_AT_BASIC, MODULE_AT_SIM } module_at_kind_t;
typedef enum { MODULE_AT_PENDING, MODULE_AT_OK, MODULE_AT_ERROR } module_at_result_t;
typedef struct {
    char line[MODULE_AT_LINE_MAX];
    size_t used;
    bool discard, damaged, saw_sim;
    module_at_kind_t kind;
    module_at_result_t result;
    module_sim_t sim, candidate;
    int cme_error;
    module_at_line_fn on_line;
    void *context;
} module_at_t;
void module_at_init(module_at_t *parser, module_at_kind_t kind);
void module_at_feed(module_at_t *parser, const uint8_t *bytes, size_t size);
#endif
