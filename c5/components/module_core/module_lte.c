#include "module_lte.h"
#include <string.h>
static void spaces(const char **p) { while (**p == ' ' || **p == '\t') ++*p; }
static bool number(const char **p, unsigned maximum, unsigned *value)
{
    spaces(p);
    if (**p < '0' || **p > '9') return false;
    unsigned n = 0;
    do {
        unsigned digit = (unsigned)(**p - '0');
        if (n > maximum / 10 || (n == maximum / 10 && digit > maximum % 10)) return false;
        n = n * 10 + digit; ++*p;
    } while (**p >= '0' && **p <= '9');
    spaces(p); *value = n;
    return true;
}
static bool comma(const char **p) { spaces(p); if (**p != ',') return false; ++*p; return true; }
static bool end(const char *p) { spaces(&p); return !*p; }
static bool prefix(const char *line, const char *name, const char **p)
{
    size_t n = strlen(name);
    if (strncmp(line, name, n)) return false;
    *p = line + n; spaces(p); return true;
}
static int nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
size_t module_lte_hex(const uint8_t *data, size_t size, char *out, size_t capacity)
{
    static const char digits[] = "0123456789ABCDEF";
    if (!out || size > MODULE_LTE_CHUNK || capacity < size * 2 + 1 || (!data && size)) return 0;
    for (size_t i = 0; i < size; ++i) { out[i*2] = digits[data[i] >> 4]; out[i*2+1] = digits[data[i] & 15]; }
    out[size*2] = 0; return size * 2;
}
bool module_lte_host_valid(const char *host)
{
    if (!host || !*host || strlen(host) > 127) return false;
    for (const char *p = host; *p; ++p)
        if (!((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
              (*p >= '0' && *p <= '9') || *p == '-' || *p == '.')) return false;
    return true;
}
bool module_lte_apn_valid(const char *apn)
{
    return apn && (!*apn || (strlen(apn) <= 100 && module_lte_host_valid(apn)));
}
static bool address4(const char *p, char *out)
{
    bool quoted = *p == '"'; if (quoted) ++p;
    const char *start = p;
    unsigned bytes[4];
    for (unsigned i = 0; i < 4; ++i) {
        if (!number(&p, 255, &bytes[i])) return false;
        if (i != 3 && *p++ != '.') return false;
    }
    size_t size = (size_t)(p - start);
    if (size >= 16 || !bytes[0] || bytes[0] >= 224) return false;
    for (size_t i = 0; i < size; ++i) if ((start[i] < '0' || start[i] > '9') && start[i] != '.') return false;
    if (quoted && *p++ != '"') return false;
    if (*p && *p != ',') return false;
    memcpy(out, start, size); out[size] = 0;
    return true;
}
bool module_lte_parse(const char *line, module_lte_event_t *e)
{
    const char *p;
    memset(e, 0, sizeof(*e));
    if (prefix(line, "+CSQ:", &p)) {
        e->kind = LTE_SIGNAL;
        return number(&p, 99, &e->value) && (e->value <= 31 || e->value == 99) && comma(&p) &&
               number(&p, 99, &e->extra) && end(p);
    }
    if (prefix(line, "+CEREG:", &p)) {
        e->kind = LTE_REGISTER;
        unsigned first;
        if (!number(&p, 10, &first)) return false;
        if (end(p)) { e->value = first; return true; }
        if (!comma(&p) || !number(&p, 10, &e->value)) return false;
        /* Read replies n,stat; optional location fields follow. Never derive ready from an unknown stat. */
        return first <= 5 && (end(p) || *p == ',');
    }
    if (prefix(line, "+CGATT:", &p)) {
        e->kind = LTE_ATTACH; return number(&p, 1, &e->value) && end(p);
    }
    if (prefix(line, "+CGACT:", &p)) {
        e->kind = LTE_PDP;
        return number(&p, 15, &e->id) && comma(&p) && number(&p, 1, &e->value) && end(p);
    }
    if (prefix(line, "+CGPADDR:", &p)) {
        e->kind = LTE_ADDRESS;
        return number(&p, 15, &e->id) && comma(&p) && address4(p, e->address);
    }
    if (prefix(line, "+CGDCONT:", &p)) {
        e->kind = LTE_CONTEXT;
        if (!number(&p, 15, &e->id) || !comma(&p)) return false;
        spaces(&p);
        if (!strncmp(p, "\"IP\"", 4)) p += 4;
        else if (!strncmp(p, "\"IPV4V6\"", 8)) p += 8;
        else if (!strncmp(p, "\"IPV6\"", 6)) p += 6;
        else return false;
        if (!comma(&p)) return false;
        spaces(&p);
        if (*p++ != '"') return false;
        const char *start = p;
        while (*p && *p != '"') ++p;
        size_t n = (size_t)(p - start);
        if (*p != '"' || n > 100) return false;
        memcpy(e->apn, start, n); e->apn[n] = 0; ++p;
        return module_lte_apn_valid(e->apn) && (end(p) || *p == ',');
    }
    if (prefix(line, "+MIPOPEN:", &p) || prefix(line, "+MIPSEND:", &p)) {
        e->kind = !strncmp(line, "+MIPOPEN:", 9) ? LTE_OPEN : LTE_SEND;
        return number(&p, 5, &e->id) && comma(&p) && number(&p, 65535, &e->value) && end(p);
    }
    if (prefix(line, "+MIPCLOSE:", &p)) {
        e->kind = LTE_CLOSE;
        return number(&p, 5, &e->id) && (end(p) || (comma(&p) && number(&p, 65535, &e->value) && end(p)));
    }
    if (prefix(line, "+MIPSTATE:", &p)) {
        e->kind = LTE_STATE;
        if (!number(&p, 5, &e->id) || !comma(&p)) return false;
        /* Exactly four remaining fields; quoted address must not shift the state field. */
        for (unsigned field = 0; field < 3; ++field) {
            bool quoted = false;
            while (*p && (*p != ',' || quoted)) { if (*p == '"') quoted = !quoted; ++p; }
            if (quoted || !comma(&p)) return false;
        }
        spaces(&p);
        if (!strcmp(p, "\"INITIAL\"") || !strcmp(p, "\"CLOSED\"")) e->value = 0;
        else if (!strcmp(p, "\"CONNECTED\"")) e->value = 1;
        else if (!strcmp(p, "\"CONNECTING\"") || !strcmp(p, "\"CLOSING\"")) e->value = 2;
        else return false;
        return true;
    }
    if (prefix(line, "+MIPRD:", &p)) {
        e->kind = LTE_READ;
        if (!number(&p, 5, &e->id) || !comma(&p) || !number(&p, 65535, &e->value)) return false;
        if (end(p)) return true; /* cache query only */
        if (!comma(&p) || !number(&p, MODULE_LTE_CHUNK, &e->extra) || !comma(&p)) return false;
        spaces(&p);
        size_t n = e->extra;
        if (strlen(p) != 2*n) return false;
        for (size_t i = 0; i < n; ++i) {
            int hi = nibble(p[i*2]), lo = nibble(p[i*2+1]);
            if (hi < 0 || lo < 0) return false;
            e->data[i] = (uint8_t)((hi << 4) | lo);
        }
        e->size = n; e->payload_present = true; return true;
    }
    if (prefix(line, "+MIPURC:", &p)) {
        if (!strncmp(p, "\"disconn\"", 9)) { p += 9; e->kind = LTE_DISCONNECT; }
        else if (!strncmp(p, "\"rtcp\"", 6)) { p += 6; e->kind = LTE_RECEIVE; }
        else return false;
        if (!comma(&p) || !number(&p, 5, &e->id) || !comma(&p) || !number(&p, 65535, &e->value)) return false;
        return end(p) || (e->kind == LTE_RECEIVE && comma(&p) && number(&p, 65535, &e->extra) && end(p));
    }
    return false;
}
