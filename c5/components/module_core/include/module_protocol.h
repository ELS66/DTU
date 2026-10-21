#ifndef MODULE_PROTOCOL_H
#define MODULE_PROTOCOL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define MODULE_FRAME_MAX 4096u
#define MODULE_PAYLOAD_MAX (MODULE_FRAME_MAX - 7u)
typedef struct {
    uint8_t command;
    const uint8_t *data;
    size_t size;
} module_frame_t;
/* A view is valid only during its callback. */
typedef void (*module_frame_fn)(void *context, const module_frame_t *frame);
typedef struct {
    uint8_t bytes[MODULE_FRAME_MAX];
    size_t used;
    uint32_t accepted, bad_lengths, bad_checksums, partial_timeouts, partial_discards;
} module_parser_t;
uint16_t module_checksum(const uint8_t *bytes, size_t size);
size_t module_encode(uint8_t command, const uint8_t *data, size_t size,
                     uint8_t *output, size_t capacity);
void module_parser_init(module_parser_t *parser);
void module_parser_reset_partial(module_parser_t *parser);
void module_parser_discard(module_parser_t *parser);
void module_parser_feed(module_parser_t *parser, const uint8_t *bytes, size_t size,
                        module_frame_fn callback, void *context);
bool module_is_request(uint8_t command);
bool module_is_event(uint8_t command);
bool module_work_state_valid(uint8_t state);
/* 9600 8N1 request wire time + response wire allowance + processing timeout. */
uint64_t module_reply_budget_ms(uint8_t command, size_t request_bytes, uint32_t processing_ms);
#endif
