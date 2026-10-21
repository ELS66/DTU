#include "module_blob.h"
#include <string.h>
uint32_t module_blob_crc32(const uint8_t *bytes, size_t size)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < size; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? UINT32_C(0xedb88320) : 0u);
    }
    return ~crc;
}
module_blob_result_t module_blob_update(module_blob_t *b, uint8_t source, const uint8_t *bytes,
                                       size_t size, uint64_t now, uint64_t event)
{
    if (!b || size > MODULE_PAYLOAD_MAX || (size && !bytes) ||
        (source != 0xb1 && source != 0xb3 && source != 0xc5) ||
        (b->known && (now < b->observed_ms || event < b->content_event))) return MODULE_BLOB_REJECTED;
    bool changed = !b->known || b->size != size || (size && memcmp(b->bytes, bytes, size));
    if (changed && b->revision == UINT64_MAX) return MODULE_BLOB_REJECTED;
    if (changed) {
        if (size) memcpy(b->bytes, bytes, size);
        if (size < b->size) memset(b->bytes + size, 0, b->size - size);
        b->size = size; b->crc32 = module_blob_crc32(bytes, size); ++b->revision;
    }
    b->known = true; b->source = source; b->format_version = 1;
    b->observed_ms = now; b->content_event = event;
    return changed ? MODULE_BLOB_CHANGED : MODULE_BLOB_UNCHANGED;
}
bool module_blob_query_current(uint64_t requested, uint64_t current) { return requested == current; }
