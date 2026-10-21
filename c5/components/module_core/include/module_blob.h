#pragma once
#include "module_protocol.h"
typedef struct {
    bool known;
    uint8_t source;
    uint16_t format_version;
    uint32_t crc32;
    uint64_t revision, observed_ms, content_event;
    size_t size;
    uint8_t bytes[MODULE_PAYLOAD_MAX];
} module_blob_t;
typedef enum { MODULE_BLOB_REJECTED, MODULE_BLOB_UNCHANGED, MODULE_BLOB_CHANGED } module_blob_result_t;
uint32_t module_blob_crc32(const uint8_t *bytes, size_t size);
/* Caller serializes access. Complete bounded copies replace the published RAM value. */
module_blob_result_t module_blob_update(module_blob_t *blob, uint8_t source, const uint8_t *bytes,
                                       size_t size, uint64_t now, uint64_t event_revision);
/* A query issued before a panel parameter event may not overwrite the event's value. */
bool module_blob_query_current(uint64_t request_event, uint64_t current_event);
