#include "module_protocol.h"
static uint16_t read_be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}
uint16_t module_checksum(const uint8_t *bytes, size_t size)
{
    uint16_t sum = 0;
    for (size_t i = 0; i < size; ++i) sum = (uint16_t)(sum + bytes[i]);
    return sum;
}
size_t module_encode(uint8_t command, const uint8_t *data, size_t size,
                     uint8_t *output, size_t capacity)
{
    if (!output || size > MODULE_PAYLOAD_MAX || capacity < size + 7u ||
        (size && !data)) return 0;
    size_t length = size + 3u;
    output[0] = output[1] = 0xac;
    output[2] = (uint8_t)(length >> 8);
    output[3] = (uint8_t)length;
    output[4] = command;
    for (size_t i = 0; i < size; ++i) output[5 + i] = data[i];
    uint16_t sum = module_checksum(output, size + 5u);
    output[5 + size] = (uint8_t)(sum >> 8);
    output[6 + size] = (uint8_t)sum;
    return size + 7u;
}
void module_parser_init(module_parser_t *p)
{
    p->used = 0;
    p->accepted = p->bad_lengths = p->bad_checksums = p->partial_timeouts = 0;
    p->partial_discards = 0;
}
void module_parser_discard(module_parser_t *p)
{
    if (p->used && p->partial_discards != UINT32_MAX) ++p->partial_discards;
    p->used = 0;
}
void module_parser_reset_partial(module_parser_t *p)
{
    if (p->used) ++p->partial_timeouts;
    p->used = 0;
}
static void drop(module_parser_t *p, size_t count)
{
    for (size_t i = count; i < p->used; ++i) p->bytes[i - count] = p->bytes[i];
    p->used -= count;
}
static void parse(module_parser_t *p, module_frame_fn callback, void *context)
{
    while (p->used) {
        if (p->bytes[0] != 0xac) { drop(p, 1); continue; }
        if (p->used < 2) return;
        if (p->bytes[1] != 0xac) { drop(p, 1); continue; }
        if (p->used < 4) return;
        size_t length = read_be16(p->bytes + 2);
        if (length < 3 || length + 4 > MODULE_FRAME_MAX) {
            ++p->bad_lengths; drop(p, 1); continue;
        }
        size_t total = length + 4;
        if (p->used < total) return;
        if (module_checksum(p->bytes, total - 2) != read_be16(p->bytes + total - 2)) {
            ++p->bad_checksums; drop(p, 1); continue;
        }
        module_frame_t view = { p->bytes[4], p->bytes + 5, total - 7 };
        ++p->accepted;
        if (callback) callback(context, &view);
        drop(p, total);
    }
}
void module_parser_feed(module_parser_t *p, const uint8_t *bytes, size_t size,
                        module_frame_fn callback, void *context)
{
    if (!p || (!bytes && size)) return;
    for (size_t i = 0; i < size; ++i) {
        if (p->used == MODULE_FRAME_MAX) drop(p, 1);
        p->bytes[p->used++] = bytes[i];
        parse(p, callback, context);
    }
}
bool module_is_request(uint8_t command)
{
    return (command >= 0xa1 && command <= 0xa4) ||
           (command >= 0xb1 && command <= 0xb5) || command == 0xc6;
}
bool module_is_event(uint8_t command)
{
    return command >= 0xc1 && command <= 0xc7 && command != 0xc6;
}
bool module_work_state_valid(uint8_t state) { return state == 0 || state == 1 || state == 3; }
uint64_t module_reply_budget_ms(uint8_t command, size_t request_bytes, uint32_t processing_ms)
{
    if (!module_is_request(command) || !request_bytes || request_bytes > MODULE_FRAME_MAX) return 0;
    size_t response_bytes = command == 0xb1 || command == 0xb3 ? MODULE_FRAME_MAX :
                            command == 0xb2 ? 11u : command >= 0xa2 && command <= 0xa4 ? 10u : 8u;
    return ((uint64_t)request_bytes * 10000 + 9599) / 9600 +
           ((uint64_t)response_bytes * 10000 + 9599) / 9600 + processing_ms;
}
