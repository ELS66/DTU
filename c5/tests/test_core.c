#include <stdio.h>
#include <string.h>
#include "module_protocol.h"
#include "module_record.h"
#include "network_policy.h"
#include "module_at.h"
#include "module_lte.h"
#include "module_indicator.h"
#include "module_runtime_policy.h"
#include "module_supervision.h"
#include "module_blob.h"
#include "module_events.h"
#include "golden_vectors.h"
static unsigned checks, received;
static module_frame_t last;
static uint8_t payload_copy[MODULE_PAYLOAD_MAX];
static module_parser_t parser;
#define CHECK(test) do { ++checks; if (!(test)) { \
    printf("FAIL line %d: %s\n", __LINE__, #test); return 1; } } while (0)
static void receive(void *context, const module_frame_t *frame)
{
    (void)context; ++received;
    last.command = frame->command; last.size = frame->size;
    memcpy(payload_copy, frame->data, frame->size);
    last.data = payload_copy;
}
static size_t unhex(const char *hex, uint8_t *out)
{
    size_t size = 0;
    while (hex[0] && hex[1]) {
        unsigned value;
        if (sscanf(hex, "%2x", &value) != 1) return 0;
        out[size++] = (uint8_t)value; hex += 2;
    }
    return size;
}
static int golden_tests(void)
{
    uint8_t frame[MODULE_FRAME_MAX], encoded[MODULE_FRAME_MAX];
    for (size_t i = 0; i < sizeof(golden_vectors) / sizeof(golden_vectors[0]); ++i) {
        size_t size = unhex(golden_vectors[i].hex, frame);
        CHECK(size >= 7);
        for (size_t split = 0; split <= size; ++split) {
            module_parser_init(&parser); received = 0;
            module_parser_feed(&parser, frame, split, receive, NULL);
            module_parser_feed(&parser, frame + split, size - split, receive, NULL);
            CHECK(received == 1);
            CHECK(last.command == frame[4] && last.size == size - 7);
            CHECK(memcmp(last.data, frame + 5, last.size) == 0);
            CHECK(parser.used == 0);
        }
        size_t n = module_encode(frame[4], frame + 5, size - 7, encoded, sizeof(encoded));
        CHECK(n == size && memcmp(frame, encoded, size) == 0);
    }
    return 0;
}
static int stream_tests(void)
{
    uint8_t data[MODULE_PAYLOAD_MAX], frame[MODULE_FRAME_MAX], second[16];
    const size_t lengths[] = {0, 1, 2, 3, 4, 8, 257, 512, MODULE_PAYLOAD_MAX};
    for (size_t j = 0; j < sizeof(lengths) / sizeof(lengths[0]); ++j) {
        for (size_t i = 0; i < lengths[j]; ++i) data[i] = (uint8_t)(i % 7 ? 0xac : 0);
        size_t size = module_encode(0xb3, data, lengths[j], frame, sizeof(frame));
        CHECK(size == lengths[j] + 7);
        module_parser_init(&parser); received = 0;
        for (size_t i = 0; i < size; ++i) module_parser_feed(&parser, frame + i, 1, receive, NULL);
        CHECK(received == 1 && last.size == lengths[j]);
        CHECK(memcmp(data, last.data, last.size) == 0);
    }
    CHECK(module_encode(1, data, MODULE_PAYLOAD_MAX + 1, frame, sizeof(frame)) == 0);
    CHECK(module_encode(1, NULL, 1, frame, sizeof(frame)) == 0);
    CHECK(module_encode(1, data, 5, frame, 11) == 0);
    uint8_t one = 1;
    size_t a = module_encode(0xa1, &one, 1, frame, sizeof(frame));
    size_t b = module_encode(0xb2, &one, 1, second, sizeof(second));
    module_parser_init(&parser); received = 0;
    uint8_t noise[] = {0, 0xac, 1, 0xac, 0xac, 0xff, 0xff, 0xac, 0xac, 0, 0};
    module_parser_feed(&parser, noise, sizeof(noise), receive, NULL);
    module_parser_feed(&parser, frame, a, receive, NULL);
    module_parser_feed(&parser, second, b, receive, NULL);
    CHECK(received == 2 && last.command == 0xb2 && parser.bad_lengths >= 2);
    module_parser_init(&parser); received = 0;
    frame[a - 1] ^= 1;
    module_parser_feed(&parser, frame, a, receive, NULL);
    module_parser_feed(&parser, second, b, receive, NULL);
    CHECK(received == 1 && parser.bad_checksums >= 1);
    module_parser_init(&parser); received = 0;
    module_parser_feed(&parser, second, 5, receive, NULL);
    module_parser_reset_partial(&parser);
    module_parser_feed(&parser, second, b, receive, NULL);
    CHECK(received == 1 && parser.partial_timeouts == 1);
    uint8_t incomplete[] = {0xac, 0xac, 0x0f, 0xfc, 0xb3};
    module_parser_init(&parser); received = 0;
    module_parser_feed(&parser, incomplete, sizeof(incomplete), receive, NULL);
    module_parser_reset_partial(&parser);
    module_parser_feed(&parser, second, b, receive, NULL);
    CHECK(received == 1);
    memset(data, 0xff, sizeof(data));
    size_t size = module_encode(0xc5, data, sizeof(data), frame, sizeof(frame));
    unsigned independent = 0;
    for (size_t i = 0; i < size - 2; ++i) independent += frame[i];
    CHECK((((unsigned)frame[size-2] << 8) | frame[size-1]) == (independent & 0xffff));
    module_parser_init(&parser); received = 0;
    module_parser_feed(&parser, frame, size, receive, NULL);
    CHECK(received == 1 && last.size == MODULE_PAYLOAD_MAX);
    return 0;
}
static int record_tests(void)
{
    module_record_t input = {
        .sequence = UINT64_C(0x0102030405060708), .boot_tag = UINT32_C(0xaabbccdd),
        .state = 3, .source_command = 0xc3, .remaining_seconds = 65535,
        .observed_uptime_ms = UINT64_C(0xfedcba9876543210),
    }, output;
    uint8_t bytes[MODULE_RECORD_SIZE], damaged[MODULE_RECORD_SIZE];
    module_record_encode(&input, bytes);
    CHECK(module_record_decode(bytes, sizeof(bytes), &output));
    CHECK(output.sequence == input.sequence && output.boot_tag == input.boot_tag);
    CHECK(output.state == 3 && output.source_command == 0xc3 && output.remaining_seconds == 65535);
    CHECK(output.observed_uptime_ms == input.observed_uptime_ms);
    CHECK(bytes[8] == 1 && bytes[15] == 8 && bytes[22] == 255 && bytes[23] == 255);
    for (size_t i = 0; i < sizeof(bytes); ++i) {
        memcpy(damaged, bytes, sizeof(bytes)); damaged[i] ^= 1;
        CHECK(!module_record_decode(damaged, sizeof(damaged), &output));
    }
    for (size_t i = 0; i < sizeof(bytes); ++i) CHECK(!module_record_decode(bytes, i, &output));
    input.sequence = 0;
    module_record_encode(&input, bytes);
    CHECK(!module_record_decode(bytes, sizeof(bytes), &output));
    input.sequence = 1; input.state = 2;
    module_record_encode(&input, bytes);
    CHECK(!module_record_decode(bytes, sizeof(bytes), &output));
    return 0;
}
static int policy_tests(void)
{
    for (int sim = MODULE_SIM_UNKNOWN; sim <= MODULE_SIM_LOCKED; ++sim) {
        CHECK(module_network_boot_action((module_sim_t)sim, true, false) == MODULE_NET_WIFI);
        CHECK(module_network_boot_action((module_sim_t)sim, true, true) == MODULE_NET_WIFI);
        CHECK(module_network_boot_action((module_sim_t)sim, false, false) == MODULE_NET_WAIT);
    }
    CHECK(module_network_boot_action(MODULE_SIM_ABSENT, false, true) == MODULE_NET_PROVISION);
    CHECK(module_network_boot_action(MODULE_SIM_PRESENT, false, true) == MODULE_NET_TRY_LTE);
    CHECK(module_network_boot_action(MODULE_SIM_UNKNOWN, false, true) == MODULE_NET_WAIT);
    CHECK(module_network_boot_action(MODULE_SIM_LOCKED, false, true) == MODULE_NET_WAIT);
    CHECK(module_is_request(0xb4) && !module_is_request(0xc1));
    CHECK(module_is_event(0xc5) && !module_is_event(0xc6));
    CHECK(!module_work_state_valid(2));
    module_boot_gate_t gate = {0};
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, false) == MODULE_NET_WAIT && !gate.closed);
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, true, false) == MODULE_NET_WIFI && gate.closed);
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, true) == MODULE_NET_WAIT);
    gate.closed = false;
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, true) == MODULE_NET_PROVISION && gate.closed);
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, true) == MODULE_NET_WAIT);
    gate.closed = false;
    CHECK(module_network_boot_step(&gate, MODULE_SIM_UNKNOWN, false, true) == MODULE_NET_WAIT && gate.closed);
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, true) == MODULE_NET_WAIT);
    gate.closed = false;
    CHECK(module_network_boot_step(&gate, MODULE_SIM_LOCKED, false, true) == MODULE_NET_WAIT && gate.closed);
    gate.closed = false;
    CHECK(module_network_boot_step(&gate, MODULE_SIM_PRESENT, false, true) == MODULE_NET_TRY_LTE && gate.closed);
    CHECK(module_network_boot_step(&gate, MODULE_SIM_ABSENT, false, true) == MODULE_NET_WAIT);
    module_sim_filter_t filter = {0};
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_UNKNOWN);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_UNKNOWN) == MODULE_SIM_UNKNOWN);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_UNKNOWN);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_ABSENT);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_ABSENT);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_LOCKED) == MODULE_SIM_LOCKED);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_UNKNOWN);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_PRESENT) == MODULE_SIM_PRESENT);
    CHECK(module_sim_confirm(&filter, MODULE_SIM_ABSENT) == MODULE_SIM_UNKNOWN);
    return 0;
}
static int at_tests(void)
{
    static const struct {
        const char *text;
        module_at_result_t result;
        module_sim_t sim;
    } cases[] = {
        {"AT+CPIN?\r\n+CPIN: READY\r\nOK\r\n", MODULE_AT_OK, MODULE_SIM_PRESENT},
        {"\r\n+CPIN: SIM PIN\r\nOK\r\n", MODULE_AT_OK, MODULE_SIM_LOCKED},
        {"+CPIN: SIM PUK\nOK\n", MODULE_AT_OK, MODULE_SIM_LOCKED},
        {"+CPIN: PH-NET PIN\rOK\r", MODULE_AT_OK, MODULE_SIM_LOCKED},
        {"+CME ERROR: 10\r\n", MODULE_AT_ERROR, MODULE_SIM_ABSENT},
        {"+CME ERROR: SIM not inserted\r\n", MODULE_AT_ERROR, MODULE_SIM_ABSENT},
        {"+CME ERROR: 13\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"+CME ERROR: 100\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"+CME ERROR: 10garbage\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"ERROR\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"NO CARRIER\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"+CPIN: READY\r\nERROR\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"+CPIN: READY\r\n", MODULE_AT_PENDING, MODULE_SIM_UNKNOWN},
        {"+CPIN: READY\r\n+CPIN: SIM PIN\r\nOK\r\n", MODULE_AT_ERROR, MODULE_SIM_UNKNOWN},
        {"+CREG: 0\r\n+CPIN: READY\r\nOK\r\n", MODULE_AT_OK, MODULE_SIM_PRESENT},
        {"+CPIN: INVALID\r\nOK\r\n", MODULE_AT_OK, MODULE_SIM_UNKNOWN},
        {"AT\r\nOK\r\n+CME ERROR: 10\r\n", MODULE_AT_OK, MODULE_SIM_UNKNOWN},
        {"\t +CPIN: READY \t\r\n OK \r\n", MODULE_AT_OK, MODULE_SIM_PRESENT},
    };
    module_at_t at;
    for (size_t i = 0; i < sizeof(cases)/sizeof(cases[0]); ++i) {
        size_t n = strlen(cases[i].text);
        for (size_t split = 0; split <= n; ++split) {
            module_at_init(&at, MODULE_AT_SIM);
            module_at_feed(&at, (const uint8_t *)cases[i].text, split);
            module_at_feed(&at, (const uint8_t *)cases[i].text + split, n - split);
            CHECK(at.result == cases[i].result);
            CHECK(at.sim == cases[i].sim);
        }
        module_at_init(&at, MODULE_AT_SIM);
        for (size_t j = 0; j < n; ++j) module_at_feed(&at, (const uint8_t *)cases[i].text+j, 1);
        CHECK(at.result == cases[i].result && at.sim == cases[i].sim);
    }
    uint8_t overflow[MODULE_AT_LINE_MAX + 40];
    memset(overflow, 'x', sizeof(overflow));
    module_at_init(&at, MODULE_AT_SIM);
    module_at_feed(&at, overflow, sizeof(overflow));
    const char *absent = "\r\n+CME ERROR: 10\r\n";
    module_at_feed(&at, (const uint8_t *)absent, strlen(absent));
    CHECK(at.damaged && at.sim == MODULE_SIM_UNKNOWN);
    uint8_t nul[] = {'+', 'C', 'P', 'I', 'N', ':', 0, '\n'};
    module_at_init(&at, MODULE_AT_SIM);
    module_at_feed(&at, nul, sizeof(nul));
    module_at_feed(&at, (const uint8_t *)absent, strlen(absent));
    CHECK(at.damaged && at.sim == MODULE_SIM_UNKNOWN);
    module_at_init(&at, MODULE_AT_BASIC);
    module_at_feed(&at, (const uint8_t *)absent, strlen(absent));
    CHECK(at.sim == MODULE_SIM_UNKNOWN && at.cme_error == 10);
    return 0;
}
static module_lte_event_t streamed_lte;
static unsigned streamed_count;
static void lte_line(void *context, const char *line)
{
    (void)context;
    module_lte_event_t event;
    if (module_lte_parse(line, &event)) { streamed_lte = event; ++streamed_count; }
}
static int lte_tests(void)
{
    static const struct { const char *line; module_lte_kind_t kind; unsigned id, value; } good[] = {
        {"+CSQ: 15,99", LTE_SIGNAL, 0, 15},
        {"+CSQ: 99,99", LTE_SIGNAL, 0, 99},
        {"+CEREG: 0,1", LTE_REGISTER, 0, 1},
        {"+CEREG: 2,5,\"1234\",\"ABCD\",7", LTE_REGISTER, 0, 5},
        {"+CEREG: 3", LTE_REGISTER, 0, 3},
        {"+CGATT: 1", LTE_ATTACH, 0, 1},
        {"+CGACT: 1,1", LTE_PDP, 1, 1},
        {"+CGACT: 2,0", LTE_PDP, 2, 0},
        {"+CGPADDR: 1,\"10.0.0.1\"", LTE_ADDRESS, 1, 0},
        {"+CGPADDR: 1,10.20.30.40", LTE_ADDRESS, 1, 0},
        {"+CGPADDR: 1,\"10.1.2.3\",\"2001:db8::1\"", LTE_ADDRESS, 1, 0},
        {"+CGDCONT: 1,\"IPV4V6\",\"cmiot\",\"0.0.0.0\",0,0", LTE_CONTEXT, 1, 0},
        {"+CGDCONT: 1,\"IP\",\"\"", LTE_CONTEXT, 1, 0},
        {"+MIPOPEN: 0,0", LTE_OPEN, 0, 0},
        {"+MIPOPEN: 0,568", LTE_OPEN, 0, 568},
        {"+MIPSEND: 0,256", LTE_SEND, 0, 256},
        {"+MIPRD: 0,19,3,00acFF", LTE_READ, 0, 19},
        {"+MIPRD: 0,0", LTE_READ, 0, 0},
        {"+MIPCLOSE: 0", LTE_CLOSE, 0, 0},
        {"+MIPCLOSE: 0,1", LTE_CLOSE, 0, 1},
        {"+MIPSTATE: 0,,,,\"INITIAL\"", LTE_STATE, 0, 0},
        {"+MIPSTATE: 0,\"TCP\",\"10.1.2.3\",1883,\"CONNECTED\"", LTE_STATE, 0, 1},
        {"+MIPSTATE: 0,\"TCP\",\"x.y\",80,\"CLOSING\"", LTE_STATE, 0, 2},
        {"+MIPURC: \"disconn\",0,3", LTE_DISCONNECT, 0, 3},
        {"+MIPURC: \"rtcp\",0,100,200", LTE_RECEIVE, 0, 100},
    };
    static const char *bad[] = {
        "+CSQ: 32,0", "+CSQ: 15", "+CSQ: 15,99x", "+CGATT: 2", "+CGACT: 1,9",
        "+CGPADDR: 1,\"0.0.0.0\"", "+CGPADDR: 1,\"256.1.2.3\"",
        "+CGPADDR: 1,\"2001:db8::1\"", "+CGPADDR: 1,\"10 .0.0.1\"", "+CGPADDR: 1,\"224.0.0.1\"",
        "+MIPOPEN: 6,0", "+MIPOPEN: 0,-1", "+MIPOPEN: 0,65536", "+MIPOPEN: 0,0,junk",
        "+MIPRD: 0,0,2,00", "+MIPRD: 0,0,1,00ff", "+MIPRD: 0,0,1,GG",
        "+MIPRD: 0,0,257,00", "+MIPRD: 0,0,1,\"00\"", "+MIPSTATE: 0,\"CONNECTED\"",
        "+MIPSTATE: 0,,,,\"CONNECTED\",junk", "+MIPURC: \"disconn\",0,3,junk",
        "+CGDCONT: 1,\"PPP\",\"cmiot\"", "+CGDCONT: 1,\"IP\",\"cmiot", "+CGDCONT: 1,\"IP\",\"x;AT\"",
        "+CEREG: 0,99", "+CEREG: 9,1", "+MIPOPEN: 0,42949672960", "ERROR"
    };
    module_lte_event_t event;
    for (size_t i = 0; i < sizeof(good)/sizeof(good[0]); ++i) {
        CHECK(module_lte_parse(good[i].line, &event));
        CHECK(event.kind == good[i].kind && event.id == good[i].id && event.value == good[i].value);
    }
    for (size_t i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i) CHECK(!module_lte_parse(bad[i], &event));
    CHECK(module_lte_parse("+CGDCONT: 1,\"IPV4V6\",\"cmiot\"", &event) && !strcmp(event.apn, "cmiot"));
    CHECK(module_lte_host_valid("iot.example.test") && module_lte_host_valid("192.168.1.10"));
    CHECK(!module_lte_host_valid("x\"\r\nAT+CFUN=0") && !module_lte_host_valid("host:123"));
    CHECK(!module_lte_host_valid("") && !module_lte_host_valid(NULL));
    CHECK(module_lte_apn_valid("") && module_lte_apn_valid("cmiot") && !module_lte_apn_valid("foo\"bar"));
    uint8_t binary[MODULE_LTE_CHUNK];
    char hex[MODULE_LTE_CHUNK*2+1], line[MODULE_LTE_CHUNK*2+64], text[MODULE_LTE_CHUNK*2+90];
    for (size_t i = 0; i < sizeof(binary); ++i) binary[i] = (uint8_t)i;
    for (size_t size = 1; size <= sizeof(binary); ++size) {
        CHECK(module_lte_hex(binary, size, hex, sizeof(hex)) == size*2);
        snprintf(line, sizeof(line), "+MIPRD: 0,123,%u,%s", (unsigned)size, hex);
        CHECK(module_lte_parse(line, &event));
        CHECK(event.payload_present && event.size == size && memcmp(event.data, binary, size) == 0);
    }
    CHECK(!module_lte_hex(binary, 1, hex, 2));
    CHECK(!module_lte_hex(binary, MODULE_LTE_CHUNK+1, hex, sizeof(hex)));
    const char *streams[] = {"OK\r\n+MIPOPEN: 0,0\r\n", "+MIPOPEN: 0,0\r\nOK\r\n"};
    module_at_t parser_at;
    for (size_t k = 0; k < 2; ++k) {
        size_t size = strlen(streams[k]);
        for (size_t split = 0; split <= size; ++split) {
            streamed_count = 0;
            module_at_init(&parser_at, MODULE_AT_BASIC);
            parser_at.on_line = lte_line;
            module_at_feed(&parser_at, (const uint8_t *)streams[k], split);
            module_at_feed(&parser_at, (const uint8_t *)streams[k]+split, size-split);
            CHECK(parser_at.result == MODULE_AT_OK && streamed_count == 1);
            CHECK(streamed_lte.kind == LTE_OPEN && streamed_lte.value == 0);
        }
    }
    snprintf(text, sizeof(text), "%s\r\nOK\r\n", line);
    streamed_count = 0; module_at_init(&parser_at, MODULE_AT_BASIC); parser_at.on_line = lte_line;
    for (size_t i = 0; i < strlen(text); ++i) module_at_feed(&parser_at, (const uint8_t *)text+i, 1);
    CHECK(parser_at.result == MODULE_AT_OK && streamed_count == 1 && !parser_at.damaged);
    CHECK(streamed_lte.size == sizeof(binary) && !memcmp(streamed_lte.data, binary, sizeof(binary)));
    const char *rejected = "+MIPOPEN: 0,0\r\nERROR\r\n";
    streamed_count = 0; module_at_init(&parser_at, MODULE_AT_BASIC); parser_at.on_line = lte_line;
    module_at_feed(&parser_at, (const uint8_t *)rejected, strlen(rejected));
    CHECK(streamed_count == 1 && parser_at.result == MODULE_AT_ERROR);
    CHECK(module_lte_parse("+MIPRD: 0,10", &event) && !event.payload_present);
    CHECK(module_lte_parse("+MIPRD: 0,0,0,", &event) && event.payload_present && event.size == 0);
    module_route_policy_t route = {0};
    CHECK(module_route_choose(&route, 0, true, true) == MODULE_LINK_WIFI);
    CHECK(module_route_choose(&route, 0, false, true) == MODULE_LINK_LTE);
    CHECK(module_route_choose(&route, 0, false, false) == MODULE_LINK_NONE);
    module_route_result(&route, MODULE_LINK_WIFI, false, 1000);
    CHECK(module_route_choose(&route, 2000, true, true) == MODULE_LINK_LTE);
    CHECK(module_route_choose(&route, 2000, true, false) == MODULE_LINK_WIFI);
    module_route_result(&route, MODULE_LINK_LTE, true, 3000);
    module_route_result(&route, MODULE_LINK_LTE, true, 29000);
    CHECK(module_route_choose(&route, 31000, true, true) == MODULE_LINK_WIFI);
    module_route_result(&route, MODULE_LINK_WIFI, true, 32000);
    CHECK(route.last_success == MODULE_LINK_WIFI && route.wifi_retry_after_ms == 0);
    CHECK(module_route_choose(&route, 33000, false, true) == MODULE_LINK_LTE);
    module_route_result(&route, MODULE_LINK_LTE, true, 34000);
    CHECK(module_route_choose(&route, 35000, true, true) == MODULE_LINK_LTE);
    CHECK(module_route_choose(&route, 64000, true, true) == MODULE_LINK_WIFI);
    return 0;
}
static int indicator_tests(void)
{
    module_indicator_t state = {0};
    module_indicator_inputs_t input = {0};
    module_indicator_output_t out;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(out.wifi == INDICATOR_STARTING && out.lte == INDICATOR_STARTING);
    CHECK(!(out.output_mask & ((1u << MODULE_LED_WIFI_BLUE) | (1u << MODULE_LED_LTE_BLUE))));
    input.wifi_initialized = true; input.wifi_ip = true;
    input.lte_started = input.lte_at_ready = input.lte_sim_fresh = input.lte_registered = true;
    input.lte_data_ready = input.lte_data_fresh = true; input.sim = MODULE_SIM_PRESENT;
    for (unsigned phase = 0; phase < 2000; phase += 25) {
        module_indicator_render(&state, &input, phase, &out);
        CHECK(out.wifi == INDICATOR_READY && out.lte == INDICATOR_READY);
        CHECK(out.output_mask == ((1u << MODULE_LED_WIFI_GREEN) | (1u << MODULE_LED_LTE_GREEN)));
    }
    input.mqtt_connected = true; input.mqtt_link = MODULE_LINK_WIFI;
    module_indicator_render(&state, &input, 0, &out);
    CHECK((out.output_mask & (1u << MODULE_LED_WIFI_BLUE)) && !(out.output_mask & (1u << MODULE_LED_LTE_BLUE)));
    input.mqtt_link = MODULE_LINK_LTE;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(!(out.output_mask & (1u << MODULE_LED_WIFI_BLUE)) && (out.output_mask & (1u << MODULE_LED_LTE_BLUE)));
    input.lte_registration_denied = true;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(out.lte == INDICATOR_FAULT && !(out.output_mask & ((1u << MODULE_LED_LTE_BLUE) | (1u << MODULE_LED_LTE_GREEN))));
    input.lte_registration_denied = false;
    input.mqtt_connected = false;
    input.wifi_ip = false; input.provisioning = true;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(out.wifi == INDICATOR_PROVISIONING && (out.output_mask & 1u));
    module_indicator_render(&state, &input, 500, &out);
    CHECK(!(out.output_mask & 1u));
    input.candidate = true;
    module_indicator_render(&state, &input, 125, &out);
    CHECK(out.wifi == INDICATOR_VERIFYING && !(out.output_mask & 1u));
    module_indicator_render(&state, &input, 250, &out);
    CHECK(out.output_mask & 1u);
    input.provisioning = input.candidate = false;
    input.sim = MODULE_SIM_ABSENT;
    const unsigned samples[] = {0, 99, 100, 199, 200, 299, 300, 1999, 2000};
    const bool absent_on[] = {true,true,false,false,true,true,false,false,true};
    for (unsigned j = 0; j < sizeof(samples)/sizeof(samples[0]); ++j) {
        module_indicator_render(&state, &input, samples[j], &out);
        CHECK(out.lte == INDICATOR_NO_SIM);
        CHECK(!!(out.output_mask & (1u << MODULE_LED_LTE_AMBER)) == absent_on[j]);
    }
    input.sim = MODULE_SIM_LOCKED;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(out.lte == INDICATOR_FAULT && !(out.output_mask & (1u << MODULE_LED_LTE_GREEN)));
    input.sim = MODULE_SIM_PRESENT;
    input.lte_data_fresh = false;
    module_indicator_render(&state, &input, 0, &out);
    CHECK(out.lte == INDICATOR_REGISTERED && !(out.output_mask & (1u << MODULE_LED_LTE_BLUE)));
    module_indicator_render(&state, &input, 500, &out);
    CHECK(!(out.output_mask & (1u << MODULE_LED_LTE_GREEN)));
    /* Contradictory/stale inputs must never assert a blue online lamp. */
    for (unsigned bits = 0; bits < 1024; ++bits) {
        input = (module_indicator_inputs_t){
            .wifi_initialized = !!(bits & 1), .wifi_ip = !!(bits & 2), .wifi_failed = !!(bits & 4),
            .provisioning = !!(bits & 8), .lte_started = true, .lte_at_ready = !!(bits & 16),
            .lte_sim_fresh = !!(bits & 32), .lte_registered = !!(bits & 64),
            .lte_data_ready = !!(bits & 128), .lte_data_fresh = !!(bits & 256),
            .lte_model_mismatch = !!(bits & 512), .sim = MODULE_SIM_PRESENT, .mqtt_connected = true,
            .mqtt_link = MODULE_LINK_WIFI,
        };
        module_indicator_render(&state, &input, 600, &out);
        bool wifi_blue = input.wifi_initialized && input.wifi_ip && !input.wifi_failed && !input.provisioning;
        CHECK(!!(out.output_mask & (1u << MODULE_LED_WIFI_BLUE)) == wifi_blue);
        CHECK(!(out.output_mask & (1u << MODULE_LED_LTE_BLUE)));
        input.mqtt_link = MODULE_LINK_LTE;
        module_indicator_render(&state, &input, 600, &out);
        bool lte_blue = input.lte_at_ready && input.lte_sim_fresh && input.lte_registered &&
                        input.lte_data_ready && input.lte_data_fresh && !input.lte_model_mismatch;
        CHECK(!!(out.output_mask & (1u << MODULE_LED_LTE_BLUE)) == lte_blue);
        CHECK(!(out.output_mask & (1u << MODULE_LED_WIFI_BLUE)));
    }
    input = (module_indicator_inputs_t){0};
    module_indicator_tx_begin(&state);
    module_indicator_render(&state, &input, 100, &out);
    CHECK((out.output_mask & (1u << MODULE_LED_TX)) && state.tx_bytes == 0);
    module_indicator_tx(&state, 100, 100, 0);
    module_indicator_render(&state, &input, 100, &out);
    CHECK(!(out.output_mask & (1u << MODULE_LED_TX)) && !state.tx_submitting);
    module_indicator_tx(&state, 100, 100, 8);
    CHECK(state.tx_bytes == 8 && state.tx_wire_end_ms == 109 && state.tx_until_ms == 184);
    module_indicator_render(&state, &input, 183, &out); CHECK(out.output_mask & (1u << MODULE_LED_TX));
    module_indicator_render(&state, &input, 184, &out); CHECK(!(out.output_mask & (1u << MODULE_LED_TX)));
    module_indicator_tx(&state, 200, 200, 4096);
    CHECK(state.tx_wire_end_ms == 4467 && state.tx_until_ms == 4542);
    module_indicator_tx(&state, 201, 201, 8);
    CHECK(state.tx_wire_end_ms == 4476 && state.tx_until_ms == 4551);
    module_indicator_rx(&state, 100, 1);
    module_indicator_render(&state, &input, 174, &out); CHECK(out.output_mask & (1u << MODULE_LED_RX));
    module_indicator_render(&state, &input, 175, &out); CHECK(!(out.output_mask & (1u << MODULE_LED_RX)));
    module_indicator_rx(&state, 160, 10);
    CHECK(state.rx_until_ms == 235 && state.rx_bytes == 11);
    module_indicator_rx(&state, 200, 0); CHECK(state.rx_until_ms == 235);
    module_indicator_tx(&state, 200, 200, 0); CHECK(state.tx_wire_end_ms == 4476);
    CHECK(!module_indicator_override(&state, 8, true, 0, 5000));
    CHECK(!module_indicator_override(&state, 0, true, 0, 0));
    CHECK(!module_indicator_override(&state, 0, true, 0, 60001));
    CHECK(module_indicator_override(&state, MODULE_LED_WIFI_BLUE, true, 100, 5000));
    module_indicator_render(&state, &input, 5099, &out);
    CHECK(out.override_mask == (1u << MODULE_LED_WIFI_BLUE) && (out.output_mask & out.override_mask));
    module_indicator_render(&state, &input, 5100, &out);
    CHECK(!out.override_mask && !(out.output_mask & (1u << MODULE_LED_WIFI_BLUE)));
    CHECK(module_indicator_override(&state, MODULE_LED_TX, false, 200, 5000));
    module_indicator_render(&state, &input, 200, &out);
    CHECK((out.automatic_mask & (1u << MODULE_LED_TX)) && !(out.output_mask & (1u << MODULE_LED_TX)));
    module_indicator_auto(&state);
    module_indicator_render(&state, &input, 200, &out);
    CHECK(!out.override_mask && (out.output_mask & (1u << MODULE_LED_TX)));
    module_indicator_test(&state, 1000);
    for (unsigned j = 0; j < MODULE_LED_COUNT; ++j) {
        module_indicator_render(&state, &input, 1000 + j*250, &out);
        CHECK(out.test_active && out.output_mask == (1u << j));
    }
    module_indicator_render(&state, &input, 2999, &out);
    CHECK(out.test_active && out.output_mask == (1u << MODULE_LED_RX));
    module_indicator_render(&state, &input, 3000, &out);
    CHECK(!out.test_active && out.output_mask == out.automatic_mask);
    module_indicator_test(&state, 4000); module_indicator_auto(&state);
    module_indicator_render(&state, &input, 4000, &out); CHECK(!out.test_active);
    module_indicator_test(&state, 4000);
    CHECK(module_indicator_override(&state, 0, true, 4100, 5000));
    module_indicator_render(&state, &input, 4100, &out); CHECK(!out.test_active);
    return 0;
}
static int runtime_policy_tests(void)
{
    module_runtime_policy_t p = {0};
    module_observation_t captured;
    module_save_reason_t reason;
    CHECK(module_observation_freshness(&p.live, 0, 5000) == MODULE_STATE_UNKNOWN);
    CHECK(module_runtime_save_due(&p, 100000, 5000) == MODULE_SAVE_NONE);
    CHECK(!module_runtime_observe(&p, 0xb2, 2, 60, false, 0));
    CHECK(!p.live.known);
    CHECK(module_runtime_observe(&p, 0xc2, 1, 60, true, 0));
    CHECK(module_observation_freshness(&p.live, 4999, 5000) == MODULE_STATE_FRESH);
    CHECK(module_observation_freshness(&p.live, 5000, 5000) == MODULE_STATE_STALE);
    CHECK(module_runtime_save_due(&p, 249, 5000) == MODULE_SAVE_NONE);
    CHECK(module_runtime_capture(&p, 250, 5000, &captured, &reason));
    CHECK(reason == MODULE_SAVE_FIRST && captured.revision == 1 && captured.observed_uptime_ms == 0);
    CHECK(module_runtime_save_due(&p, 260, 5000) == MODULE_SAVE_NONE);
    CHECK(!module_runtime_save_finished(&p, 999, true, 260) && p.saving);
    CHECK(module_runtime_observe(&p, 0xc3, 3, 59, true, 260));
    CHECK(captured.state == 1 && captured.remaining_seconds == 60); /* immutable in-flight copy */
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 270));
    CHECK(p.critical_pending && p.critical_since_ms == 260 && p.saved_revision == 1);
    CHECK(module_runtime_save_due(&p, 2269, 5000) == MODULE_SAVE_NONE);
    CHECK(module_runtime_capture(&p, 2270, 5000, &captured, &reason));
    CHECK(reason == MODULE_SAVE_CRITICAL && captured.state == 3 && captured.remaining_seconds == 59);
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 2270) && !p.critical_pending);
    CHECK(!module_runtime_save_finished(&p, captured.revision, true, 2271));
    /* Duplicate urgent events refresh observations, but do not create critical writes. */
    for (unsigned t = 2300; t < 12000; t += 100) {
        CHECK(module_runtime_observe(&p, 0xb2, 3, 59, false, t));
        CHECK(module_runtime_observe(&p, 0xc3, 3, 59, true, t));
        CHECK(module_runtime_save_due(&p, t, 5000) == MODULE_SAVE_NONE);
    }
    CHECK(p.duplicate_events == 97 && !p.critical_pending);
    CHECK(module_runtime_observe(&p, 0xc3, 3, 59, true, 12270));
    CHECK(module_runtime_capture(&p, 12270, 5000, &captured, &reason));
    CHECK(reason == MODULE_SAVE_PERIODIC && captured.observed_uptime_ms == 12270);
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 12270));
    /* A failure cannot advance the committed revision or erase a later observation. */
    CHECK(module_runtime_observe(&p, 0xc4, 0, 59, true, 13000));
    CHECK(module_runtime_capture(&p, 14270, 5000, &captured, &reason));
    uint64_t old_saved = p.saved_revision;
    CHECK(module_runtime_observe(&p, 0xc2, 1, 120, true, 14280));
    CHECK(module_runtime_save_finished(&p, captured.revision, false, 14300));
    CHECK(p.saved_revision == old_saved && p.last_success_ms == 12270 && p.retry_after_ms == 19300);
    CHECK(module_runtime_save_due(&p, 19299, 5000) == MODULE_SAVE_NONE);
    CHECK(module_runtime_observe(&p, 0xb2, 1, 115, false, 19300));
    CHECK(module_runtime_capture(&p, 19300, 5000, &captured, &reason));
    CHECK(captured.state == 1 && captured.remaining_seconds == 115);
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 19300));
    CHECK(module_runtime_save_due(&p, 40000, 5000) == MODULE_SAVE_NONE); /* stale and unchanged */
    CHECK(p.live.observed_uptime_ms == 19300);
    CHECK(module_runtime_observe(&p, 0xb2, 1, 94, false, 40000));
    CHECK(module_runtime_capture(&p, 40000, 5000, &captured, &reason));
    CHECK(reason == MODULE_SAVE_PERIODIC && captured.observed_uptime_ms == 40000);
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 40000));
    CHECK(!module_runtime_observe(&p, 0xb2, 1, 95, false, 39999));
    CHECK(module_observation_freshness(&p.live, 39999, 5000) == MODULE_STATE_STALE);
    CHECK(module_observation_freshness(&p.live, 40000, 0) == MODULE_STATE_STALE);
    p.live.revision = UINT64_MAX;
    CHECK(!module_runtime_observe(&p, 0xb2, 1, 1, false, 40001));
    /* Failed very first write stays pending and cannot reuse historical RAM state as live. */
    memset(&p, 0, sizeof(p));
    CHECK(module_runtime_observe(&p, 0xb2, 0, 0, false, 100));
    CHECK(module_runtime_capture(&p, 350, 5000, &captured, &reason));
    CHECK(module_runtime_save_finished(&p, captured.revision, false, 360));
    CHECK(!p.has_saved && !p.saved_revision && p.retry_after_ms == 5360);
    CHECK(module_runtime_save_due(&p, 5360, 5000) == MODULE_SAVE_NONE); /* data itself expired */
    CHECK(module_runtime_observe(&p, 0xb2, 0, 0, false, 5400));
    CHECK(module_runtime_capture(&p, 5400, 5000, &captured, &reason) && reason == MODULE_SAVE_FIRST);
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 5400));
    /* Healthy countdown: repeated fresh observations still yield a 10-second cadence. */
    memset(&p, 0, sizeof(p));
    unsigned writes = 0;
    uint64_t last_write = 0;
    for (unsigned t = 0; t <= 25000; t += 25) {
        CHECK(module_runtime_observe(&p, 0xb2, 1, (uint16_t)(100 - t/1000), false, t));
        if (module_runtime_capture(&p, t, 5000, &captured, &reason)) {
            if (writes) CHECK(t - last_write == 10000 && reason == MODULE_SAVE_PERIODIC);
            else CHECK(t == 250 && reason == MODULE_SAVE_FIRST);
            CHECK(captured.observed_uptime_ms == t && captured.remaining_seconds == 100 - t/1000);
            CHECK(module_runtime_save_finished(&p, captured.revision, true, t));
            last_write = t; ++writes;
        }
    }
    CHECK(writes == 3);
    /* Panel-event storm: preserve latest state, never starve debounce, cap write frequency. */
    memset(&p, 0, sizeof(p)); writes = 0; last_write = 0;
    for (unsigned t = 0; t <= 20000; t += 25) {
        uint8_t work = (t/25)%2 ? 3 : 1;
        CHECK(module_runtime_observe(&p, work == 1 ? 0xc2 : 0xc3, work, 500, true, t));
        if (module_runtime_capture(&p, t, 5000, &captured, &reason)) {
            if (writes) CHECK(t - last_write >= 2000 && t - last_write <= 10000);
            CHECK(captured.state == work && captured.observed_uptime_ms == t);
            CHECK(module_runtime_save_finished(&p, captured.revision, true, t));
            last_write = t; ++writes;
        }
    }
    CHECK(writes == 10 && p.coalesced_changes > 100);
    /* Unchanged countdown while a write is in flight remains periodic, not urgent. */
    memset(&p, 0, sizeof(p));
    CHECK(module_runtime_observe(&p, 0xb2, 1, 60, false, 0));
    CHECK(module_runtime_capture(&p, 250, 5000, &captured, &reason));
    CHECK(module_runtime_observe(&p, 0xb2, 1, 59, false, 260));
    CHECK(module_runtime_save_finished(&p, captured.revision, true, 270));
    CHECK(p.live.revision > p.saved_revision && !p.critical_pending);
    CHECK(module_runtime_save_due(&p, 2270, 5000) == MODULE_SAVE_NONE);
    return 0;
}
static int peer_health_tests(void)
{
    CHECK(module_state_timeout_ms(5000, 1000, 500) == 5000);
    CHECK(module_contact_timeout_ms(5000, 1000, 500) == 7767);
    CHECK(module_state_timeout_ms(5000, 60000, 500) == 180500);
    CHECK(module_contact_timeout_ms(180500, 60000, 500) == 184767);
    CHECK(module_state_timeout_ms(300000, 1000, 500) == 300000);
    CHECK(module_contact_timeout_ms(300000, 1000, 500) == 300000);
    module_peer_t peer = {0};
    CHECK(module_peer_state(&peer, 0, 5000) == MODULE_CONTACT_NOT_STARTED);
    module_peer_start(&peer, 100);
    CHECK(module_peer_state(&peer, 5099, 5000) == MODULE_CONTACT_WAITING);
    module_peer_tick(&peer, 5100, 5000);
    CHECK(module_peer_state(&peer, 5100, 5000) == MODULE_CONTACT_OFFLINE && peer.loss_events == 1);
    module_peer_tick(&peer, 5200, 5000); CHECK(peer.loss_events == 1);
    module_peer_timeout(&peer); module_peer_timeout(&peer);
    module_peer_received(&peer, 5300, 5000, false);
    CHECK(peer.recoveries == 1 && peer.consecutive_timeouts == 2 && peer.ever_valid);
    CHECK(module_peer_state(&peer, 5300, 5000) == MODULE_CONTACT_ONLINE);
    module_peer_received(&peer, 5400, 5000, true);
    CHECK(!peer.consecutive_timeouts && peer.last_valid_ms == 5400 && peer.recoveries == 1);
    CHECK(module_peer_state(&peer, 10399, 5000) == MODULE_CONTACT_ONLINE);
    CHECK(module_peer_state(&peer, 10400, 5000) == MODULE_CONTACT_OFFLINE);
    module_peer_received(&peer, 10400, 5000, true); /* receive also notices an unpolled outage */
    CHECK(peer.loss_events == 2 && peer.recoveries == 2 && !peer.loss_latched);
    module_peer_tick(&peer, 10401, 5000); CHECK(peer.loss_events == 2);
    CHECK(module_peer_state(&peer, 10399, 5000) == MODULE_CONTACT_OFFLINE);
    CHECK(module_peer_state(&peer, 10400, 0) == MODULE_CONTACT_OFFLINE);
    peer.consecutive_timeouts = UINT32_MAX; module_peer_timeout(&peer);
    CHECK(peer.consecutive_timeouts == UINT32_MAX);
    peer.loss_events = peer.recoveries = UINT32_MAX;
    module_peer_tick(&peer, 16000, 5000);
    module_peer_received(&peer, 16000, 5000, false);
    CHECK(peer.loss_events == UINT32_MAX && peer.recoveries == UINT32_MAX);
    return 0;
}
static int supervision_tests(void)
{
    module_watch_t w = {0};
    CHECK(!module_watch_evaluate(&w, 0));
    CHECK(!module_watch_enable(NULL, 0, 1, 0));
    CHECK(!module_watch_enable(&w, MODULE_WATCH_COUNT, 1, 0));
    CHECK(!module_watch_enable(&w, 0, 0, 0));
    CHECK(!module_watch_progress(&w, 0, 0));
    CHECK(module_watch_enable(&w, MODULE_WATCH_FIELD, 15000, 0));
    CHECK(!module_watch_enable(&w, MODULE_WATCH_FIELD, 15000, 1));
    CHECK(module_watch_enable(&w, MODULE_WATCH_MODEM, 45000, 0));
    /* The field worker remains healthy without a board; modem AT waits may last 30s. */
    for (uint64_t t = 100; t <= 90000; t += 100) {
        CHECK(module_watch_progress(&w, MODULE_WATCH_FIELD, t));
        if (t % 30000 == 0) CHECK(module_watch_progress(&w, MODULE_WATCH_MODEM, t));
        CHECK(!module_watch_evaluate(&w, t));
    }
    CHECK(!module_watch_progress(&w, MODULE_WATCH_FIELD, 89999));
    CHECK(!module_watch_evaluate(&w, 104999));
    CHECK(module_watch_evaluate(&w, 105000) == (1u << MODULE_WATCH_FIELD));
    CHECK(w.fault_ms == 105000);
    CHECK(module_watch_progress(&w, MODULE_WATCH_FIELD, 105001));
    module_watch_disable(&w, MODULE_WATCH_FIELD);
    CHECK(module_watch_evaluate(&w, 105002) == (1u << MODULE_WATCH_FIELD)); /* fault cannot be hidden */
    CHECK(!module_watch_enable(&w, MODULE_WATCH_STORE, 10000, 105002));
    memset(&w, 0, sizeof(w));
    CHECK(module_watch_enable(&w, MODULE_WATCH_LED, 2000, 50));
    CHECK(module_watch_enable(&w, MODULE_WATCH_NETWORK, 15000, 50));
    module_watch_disable(&w, MODULE_WATCH_NETWORK); /* failed creation is explicitly disabled */
    CHECK(module_watch_evaluate(&w, 2049) == 0);
    CHECK(module_watch_evaluate(&w, 2050) == (1u << MODULE_WATCH_LED)); /* never scheduled */
    memset(&w, 0, sizeof(w));
    CHECK(module_watch_enable(&w, 0, 100, 200));
    CHECK(module_watch_evaluate(&w, 199) == 1); /* monotonic clock violation fails closed */
    memset(&w, 0, sizeof(w));
    for (unsigned i = 0; i < MODULE_WATCH_COUNT; ++i) CHECK(module_watch_enable(&w, i, 100, 0));
    CHECK(module_watch_evaluate(&w, 100) == 31);
    w.slots[0].advances = UINT32_MAX;
    CHECK(module_watch_progress(&w, 0, 200) && w.slots[0].advances == UINT32_MAX);
    module_watch_disable(NULL, 0); module_watch_disable(&w, 99);
    CHECK(!module_watch_progress(&w, 99, 200));
    return 0;
}
static int uart_recovery_tests(void)
{
    CHECK(module_reply_budget_ms(0xb1, 8, 500) == 4776);
    CHECK(module_reply_budget_ms(0xb3, 8, 500) == 4776);
    CHECK(module_reply_budget_ms(0xb2, 8, 500) == 521);
    CHECK(module_reply_budget_ms(0xa2, 8, 500) == 520);
    CHECK(module_reply_budget_ms(0xb4, 4096, 500) == 4776);
    CHECK(!module_reply_budget_ms(0xc5, 8, 500));
    CHECK(!module_reply_budget_ms(0xb3, 4097, 500));
    CHECK(!module_reply_budget_ms(0xb3, 0, 500));
    module_uart_health_t h = {0};
    CHECK(!module_uart_good(&h, 0));
    CHECK(!module_uart_pressure(&h, 11, 16) && h.pressure_batches == 0);
    CHECK(!module_uart_pressure(&h, 12, 16) && h.pressure_batches == 1 && h.queue_peak == 12);
    CHECK(module_uart_pressure(&h, 16, 16) && h.queue_peak == 16);
    CHECK(!module_uart_pressure(&h, 0, 0));
    module_uart_fault(&h, MODULE_UART_FIFO | MODULE_UART_FRAME, 100, 500);
    CHECK(h.recovering && h.fault_batches == 1 && h.consecutive_faults == 1 && h.fifo == 1 && h.frame == 1);
    CHECK(!module_uart_good(&h, 599));
    module_uart_fault(&h, MODULE_UART_PARITY | MODULE_UART_BREAK | MODULE_UART_BUFFER | MODULE_UART_QUEUE_FULL | MODULE_UART_READ, 550, 500);
    CHECK(h.fault_batches == 2 && h.consecutive_faults == 2 && h.last_fault_ms == 550 && h.guard_until_ms == 1050);
    CHECK(h.parity == 1 && h.breaks == 1 && h.buffer == 1 && h.queue_full == 1 && h.read_errors == 1);
    CHECK(!module_uart_good(&h, 1049));
    CHECK(module_uart_good(&h, 1050) && !h.recovering && !h.consecutive_faults && h.recoveries == 1);
    CHECK(!module_uart_good(&h, 2000) && h.recoveries == 1);
    /* A UART error between frame fragments must not assemble an apparently valid message. */
    uint8_t body[] = {0x00, 0xac, 0xac, 0x55}, frame[32];
    size_t n = module_encode(0xc5, body, sizeof(body), frame, sizeof(frame));
    module_parser_init(&parser); received = 0;
    module_parser_feed(&parser, frame, 6, receive, NULL);
    CHECK(!received && parser.used == 6);
    module_parser_discard(&parser);
    CHECK(parser.partial_discards == 1 && !parser.partial_timeouts && !parser.used);
    module_parser_feed(&parser, frame + 6, n - 6, receive, NULL);
    CHECK(!received);
    module_parser_feed(&parser, frame, n, receive, NULL);
    CHECK(received == 1 && last.command == 0xc5 && last.size == sizeof(body) && !memcmp(last.data, body, sizeof(body)));
    h.fault_batches = h.consecutive_faults = h.frame = UINT32_MAX;
    module_uart_fault(&h, MODULE_UART_FRAME, UINT64_MAX - 10, 500);
    CHECK(h.guard_until_ms == UINT64_MAX && h.fault_batches == UINT32_MAX && h.consecutive_faults == UINT32_MAX && h.frame == UINT32_MAX);
    CHECK(!module_uart_good(&h, UINT64_MAX - 1) && module_uart_good(&h, UINT64_MAX));
    module_uart_fault(&h, 0, 10, 500);
    CHECK(!h.recovering);
    return 0;
}
static int blob_tests(void)
{
    static module_blob_t blob;
    static uint8_t raw[MODULE_PAYLOAD_MAX + 1];
    CHECK(module_blob_crc32((const uint8_t *)"123456789", 9) == UINT32_C(0xcbf43926));
    CHECK(module_blob_crc32(NULL, 0) == 0);
    for (size_t i = 0; i < sizeof(raw); ++i) raw[i] = (uint8_t)(i % 5 == 0 ? 0xac : i);
    CHECK(module_blob_update(&blob, 0xb1, raw, 4, 1, 0) == MODULE_BLOB_CHANGED);
    CHECK(blob.known && blob.size == 4 && blob.source == 0xb1 && blob.format_version == 1 && blob.revision == 1);
    CHECK(module_blob_update(&blob, 0xb1, raw, 4, 2, 0) == MODULE_BLOB_UNCHANGED);
    CHECK(blob.revision == 1 && blob.observed_ms == 2);
    /* All legal opaque lengths including 0, binary zero, embedded AC AC and the full event payload. */
    memset(&blob, 0, sizeof(blob));
    for (size_t size = 0; size <= MODULE_PAYLOAD_MAX; ++size) {
        CHECK(module_blob_update(&blob, 0xc5, raw, size, size, size) == MODULE_BLOB_CHANGED);
        CHECK(blob.size == size && blob.crc32 == module_blob_crc32(raw, size) && blob.revision == size + 1);
        CHECK(!memcmp(blob.bytes, raw, size));
    }
    module_blob_t before = blob;
    CHECK(module_blob_update(&blob, 0xc5, raw, sizeof(raw), 5000, 5000) == MODULE_BLOB_REJECTED);
    CHECK(!memcmp(&blob, &before, sizeof(blob)));
    CHECK(module_blob_update(&blob, 0xb3, NULL, 1, 5000, 5000) == MODULE_BLOB_REJECTED);
    CHECK(module_blob_update(&blob, 0xb4, raw, 2, 5000, 5000) == MODULE_BLOB_REJECTED);
    CHECK(module_blob_update(&blob, 0xb3, raw, 2, 1, 5000) == MODULE_BLOB_REJECTED);
    CHECK(module_blob_update(&blob, 0xb3, raw, 2, 5000, 1) == MODULE_BLOB_REJECTED);
    CHECK(module_blob_query_current(1, 1) && !module_blob_query_current(1, 2));
    uint64_t pending_query_event = blob.content_event;
    CHECK(module_blob_update(&blob, 0xc5, raw, 2, 5000, 5000) == MODULE_BLOB_CHANGED);
    CHECK(!module_blob_query_current(pending_query_event, blob.content_event)); /* older B3 must be ignored */
    CHECK(blob.bytes[2] == 0 && blob.bytes[MODULE_PAYLOAD_MAX-1] == 0); /* shorter replacement removes tail */
    CHECK(module_blob_update(&blob, 0xb3, raw, 2, 5001, 5000) == MODULE_BLOB_UNCHANGED);
    CHECK(blob.source == 0xb3 && blob.observed_ms == 5001);
    blob.revision = UINT64_MAX;
    CHECK(module_blob_update(&blob, 0xb3, raw, 3, 5002, 5000) == MODULE_BLOB_REJECTED);
    CHECK(module_blob_update(&blob, 0xc5, raw, 2, 5002, 5001) == MODULE_BLOB_UNCHANGED && blob.revision == UINT64_MAX);
    CHECK(module_blob_update(&blob, 0xc5, NULL, 0, 5003, 5002) == MODULE_BLOB_REJECTED); /* revision exhausted */
    memset(&blob, 0, sizeof(blob));
    CHECK(module_blob_update(&blob, 0xc5, NULL, 0, 0, 0) == MODULE_BLOB_CHANGED);
    CHECK(blob.known && !blob.size && blob.crc32 == 0);
    CHECK(module_blob_update(NULL, 0xc5, NULL, 0, 0, 0) == MODULE_BLOB_REJECTED);
    return 0;
}
static int event_log_tests(void)
{
    static module_events_t events;
    module_events_page_t page, preserved;
    module_events_init(&events);
    CHECK(module_events_page(&events, 0, 16, &page));
    CHECK(!page.count && !page.retained && !page.oldest && !page.latest && !page.gap && !page.cursor_ahead);
    CHECK(!module_events_append(NULL, 1, 2, 3, 0));
    CHECK(!module_events_append(&events, 0, 2, 3, 0) && events.rejected == 1);
    CHECK(!module_events_page(&events, 0, 0, &page));
    CHECK(!module_events_page(&events, 0, 17, &page));
    CHECK(!module_events_page(NULL, 0, 1, &page));
    CHECK(!module_events_page(&events, 0, 1, NULL));
    for (uint64_t i = 1; i <= 1000; ++i) {
        CHECK(module_events_append(&events, (uint32_t)(i % 20 + 1), (uint32_t)i, (uint32_t)(i*2), i*10));
        if (i == 64) {
            CHECK(module_events_page(&events, 0, 16, &page));
            CHECK(page.oldest == 1 && page.latest == 64 && !page.overwritten && !page.gap);
        }
    }
    CHECK(module_events_page(&events, 0, 7, &page));
    CHECK(page.count == 7 && page.retained == 64 && page.oldest == 937 && page.latest == 1000 && page.overwritten == 936 && page.gap);
    CHECK(page.next_cursor == 943 && page.rejected == 1);
    preserved = page;
    uint64_t cursor = 936;
    unsigned exported = 0;
    do {
        CHECK(module_events_page(&events, cursor, 7, &page));
        CHECK(!page.gap && !page.cursor_ahead && page.count <= 7);
        for (size_t i = 0; i < page.count; ++i) {
            const module_event_t *e = &page.entries[i];
            CHECK(e->sequence == cursor + i + 1 && e->detail == e->sequence && e->value == e->sequence * 2 && e->uptime_ms == e->sequence * 10);
            ++exported;
        }
        cursor = page.next_cursor;
    } while (page.count);
    CHECK(exported == 64 && cursor == 1000);
    CHECK(module_events_page(&events, 1001, 16, &page) && page.cursor_ahead && !page.count && page.next_cursor == 1001);
    CHECK(module_events_append(&events, 10, 1, 0, 9999)); /* delayed task append: monotonic clamp */
    CHECK(module_events_page(&events, 1000, 16, &page) && page.entries[0].uptime_ms == 10000 && page.next_cursor == 1001);
    CHECK(preserved.entries[0].sequence == 937 && preserved.latest == 1000); /* captured page is independent */
    CHECK(module_events_page(&events, 936, 16, &page) && page.gap && page.oldest == 938);
    events.last_sequence = UINT64_MAX - 1;
    CHECK(module_events_append(&events, 60, 31, 0, 10001));
    CHECK(events.last_sequence == UINT64_MAX);
    CHECK(!module_events_append(&events, 60, 31, 0, 10002) && events.rejected == 2);
    events.rejected = UINT32_MAX; events.overwritten = UINT64_MAX; events.last_sequence = 1001;
    CHECK(!module_events_append(&events, 0, 0, 0, 10002) && events.rejected == UINT32_MAX);
    CHECK(module_events_append(&events, 1, 0, 0, 10002) && events.overwritten == UINT64_MAX);
    module_events_init(&events);
    CHECK(!events.count && !events.last_sequence && !events.rejected && !events.overwritten);
    return 0;
}
int main(void)
{
    if (golden_tests() || stream_tests() || record_tests() || policy_tests() || at_tests() || lte_tests() || indicator_tests() ||
        runtime_policy_tests() || peer_health_tests() || supervision_tests() || uart_recovery_tests() || blob_tests() || event_log_tests()) return 1;
    printf("PASS: %u checks; protocol/network/LED, runtime, supervision, UART/cache and bounded diagnostic events\n", checks);
    return 0;
}
