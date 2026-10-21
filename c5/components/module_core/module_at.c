#include "module_at.h"
#include <stdlib.h>
#include <string.h>
void module_at_init(module_at_t *p, module_at_kind_t kind)
{
    memset(p, 0, sizeof(*p));
    p->kind = kind;
    p->cme_error = -1;
}
static void line_received(module_at_t *p)
{
    p->line[p->used] = 0;
    char *line = p->line;
    while (*line == ' ' || *line == '\t') ++line;
    size_t n = strlen(line);
    while (n && (line[n-1] == ' ' || line[n-1] == '\t')) line[--n] = 0;
    if (p->on_line) p->on_line(p->context, line);
    if (p->result != MODULE_AT_PENDING) return;
    if (!strcmp(line, "OK")) {
        p->result = p->damaged ? MODULE_AT_ERROR : MODULE_AT_OK;
        if (!p->damaged && p->saw_sim) p->sim = p->candidate;
    } else if (!strncmp(line, "+CME ERROR:", 11)) {
        char *value = line + 11, *end;
        while (*value == ' ') ++value;
        long code = strtol(value, &end, 10);
        if (end != value && !*end && code >= 0 && code <= 65535) p->cme_error = (int)code;
        p->result = MODULE_AT_ERROR;
        if (p->kind == MODULE_AT_SIM && !p->damaged &&
            (p->cme_error == 10 || !strcmp(value, "SIM not inserted")))
            p->sim = MODULE_SIM_ABSENT;
    } else if (!strcmp(line, "ERROR") || !strcmp(line, "NO CARRIER")) {
        p->result = MODULE_AT_ERROR;
    } else if (p->kind == MODULE_AT_SIM && !strncmp(line, "+CPIN:", 6)) {
        char *value = line + 6;
        while (*value == ' ') ++value;
        module_sim_t sim = MODULE_SIM_UNKNOWN;
        if (!strcmp(value, "READY")) sim = MODULE_SIM_PRESENT;
        else if (!strcmp(value, "SIM PIN") || !strcmp(value, "SIM PUK") ||
                 !strcmp(value, "SIM PIN2") || !strcmp(value, "SIM PUK2") ||
                 !strcmp(value, "PH-SIM PIN") || !strcmp(value, "PH-NET PIN") ||
                 !strcmp(value, "PH-NET PUK")) sim = MODULE_SIM_LOCKED;
        /* Conflicting duplicate CPIN lines cannot establish absence/presence. */
        if (p->saw_sim && p->candidate != sim) p->damaged = true;
        p->saw_sim = true;
        p->candidate = sim;
    }
}
void module_at_feed(module_at_t *p, const uint8_t *bytes, size_t size)
{
    for (size_t i = 0; i < size && (p->result == MODULE_AT_PENDING || p->on_line); ++i) {
        uint8_t c = bytes[i];
        if (c == '\r' || c == '\n') {
            if (!p->discard && p->used) line_received(p);
            p->used = 0; p->discard = false;
        } else if (!p->discard) {
            if (!c || (c < 32 && c != '\t') || c >= 127 || p->used == sizeof(p->line)-1) {
                p->damaged = true; p->discard = true; p->used = 0;
            } else p->line[p->used++] = (char)c;
        }
    }
}
