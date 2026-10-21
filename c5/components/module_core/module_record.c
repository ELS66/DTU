#include "module_record.h"
#include "module_protocol.h"
static void write_be(uint8_t *p, uint64_t value, unsigned count)
{
    for (unsigned i = count; i; --i) { p[i - 1] = (uint8_t)value; value >>= 8; }
}
static uint64_t read_be(const uint8_t *p, unsigned count)
{
    uint64_t value = 0;
    for (unsigned i = 0; i < count; ++i) value = (value << 8) | p[i];
    return value;
}
static uint32_t crc32(const uint8_t *p, size_t size)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < size; ++i) {
        crc ^= p[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? UINT32_C(0xedb88320) : 0u);
    }
    return ~crc;
}
void module_record_encode(const module_record_t *r, uint8_t p[MODULE_RECORD_SIZE])
{
    p[0] = 'C'; p[1] = '5'; p[2] = 'R'; p[3] = 'S';
    write_be(p + 4, 1, 2);
    write_be(p + 6, MODULE_RECORD_SIZE, 2);
    write_be(p + 8, r->sequence, 8);
    write_be(p + 16, r->boot_tag, 4);
    p[20] = r->state; p[21] = r->source_command;
    write_be(p + 22, r->remaining_seconds, 2);
    write_be(p + 24, r->observed_uptime_ms, 8);
    write_be(p + 32, crc32(p, 32), 4);
}
bool module_record_decode(const uint8_t *p, size_t size, module_record_t *r)
{
    if (!p || !r || size != MODULE_RECORD_SIZE || p[0] != 'C' || p[1] != '5' ||
        p[2] != 'R' || p[3] != 'S' || read_be(p + 4, 2) != 1 ||
        read_be(p + 6, 2) != MODULE_RECORD_SIZE || !module_work_state_valid(p[20]) ||
        read_be(p + 32, 4) != crc32(p, 32) || read_be(p + 8, 8) == 0) return false;
    r->sequence = read_be(p + 8, 8);
    r->boot_tag = (uint32_t)read_be(p + 16, 4);
    r->state = p[20]; r->source_command = p[21];
    r->remaining_seconds = (uint16_t)read_be(p + 22, 2);
    r->observed_uptime_ms = read_be(p + 24, 8);
    return true;
}
