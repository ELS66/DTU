"""Bench-tool checks use virtual clocks and memory transports; no COM port is opened."""
import contextlib
import io
from pathlib import Path
import random
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import board_simulator as sim


class CodecTests(unittest.TestCase):
    def test_workbook_golden_frames_and_every_split(self):
        source = (Path(__file__).parent / "golden_vectors.h").read_text(encoding="utf-8")
        fixtures = [bytes.fromhex(value) for value in re.findall(r'\{"([A-Fa-f0-9]+)"\}', source)]
        self.assertEqual(len(fixtures), 18)
        for raw in fixtures:
            expected = sim.Frame(raw[4], raw[5:-2])
            self.assertEqual(sim.encode(expected), raw)
            for split in range(len(raw)+1):
                parser = sim.Stream()
                result = parser.feed(raw[:split], 0) + parser.feed(raw[split:], .001)
                self.assertEqual(result, [expected])

    def test_noise_checksum_and_length_resync(self):
        good = bytes.fromhex("ACAC0007B2010100640277")
        bad = good[:-1] + bytes([good[-1] ^ 1])
        parser = sim.Stream()
        frames = parser.feed(b"\x00\xff\xac\x00\xac\xac\x00\x02" + bad + good, 0)
        self.assertEqual(frames, [sim.Frame(0xb2, bytes.fromhex("01010064"))])
        self.assertGreater(parser.bad_lengths, 0)
        self.assertGreater(parser.bad_checksums, 0)

    def test_partial_gap_discards_old_fragment(self):
        raw = sim.encode(sim.Frame(0xc5, b"\x00\xac\xac\x55"))
        parser = sim.Stream()
        self.assertEqual(parser.feed(raw[:6], 0), [])
        self.assertEqual(parser.feed(raw[6:], .25), [])
        self.assertEqual(parser.partial_timeouts, 1)
        self.assertEqual(parser.feed(raw, .251), [sim.Frame(0xc5, b"\x00\xac\xac\x55")])

    def test_empty_and_longest_frames(self):
        for size in (0, 1, 4088, 4089):
            frame = sim.Frame(0xc5, sim.pattern(size))
            raw = sim.encode(frame)
            self.assertEqual(len(raw), size+7)
            self.assertEqual(sim.Stream().feed(raw, 0), [frame])
        with self.assertRaises(ValueError):
            sim.encode(sim.Frame(0xc5, b"x"*4090))
        with self.assertRaises(ValueError):
            sim.encode(sim.Frame(256, b""))
        with self.assertRaises(ValueError):
            sim.pattern(-1)

    def test_seeded_binary_stream_chunks(self):
        generator = random.Random(20261020)
        expected = [sim.Frame(0xc5, generator.randbytes(generator.randrange(100))) for _ in range(100)]
        data = b"".join(sim.encode(frame) for frame in expected)
        actual, parser, offset = [], sim.Stream(), 0
        while offset < len(data):
            size = generator.randrange(1, 257)
            actual += parser.feed(data[offset:offset+size], offset/100000)
            offset += size
        self.assertEqual(actual, expected)
        self.assertLessEqual(len(parser.buffer), sim.FRAME_MAX)


class BoardTests(unittest.TestCase):
    def test_countdown_expires_once(self):
        board = sim.Mainboard(state=1, remaining=3)
        self.assertEqual(board.advance(.9), [])
        self.assertEqual(board.remaining, 3)
        self.assertEqual(board.advance(1.9), [])
        self.assertEqual(board.remaining, 2)
        self.assertEqual(board.advance(3), [sim.Frame(0xc1, b"\x01")])
        self.assertEqual(board.advance(4), [])
        self.assertEqual(board.receive(sim.Frame(0xb2, b"\x01"), 5), [sim.Frame(0xb2, b"\x01\x00\x00\x00")])

    def test_start_pause_resume_stop_preserves_remaining(self):
        board = sim.Mainboard()
        self.assertEqual(board.receive(sim.Frame(0xa1, b"\x00\x64"), 0), [sim.Frame(0xa1, b"\x01")])
        self.assertEqual(board.receive(sim.Frame(0xa3, b"\x01"), 3), [sim.Frame(0xa3, b"\x01\x00\x61")])
        board.advance(5)
        self.assertEqual((board.state, board.remaining), (3, 97))
        self.assertEqual(board.receive(sim.Frame(0xa4, b"\x01"), 6), [sim.Frame(0xa4, b"\x01\x00\x61")])
        self.assertEqual(board.receive(sim.Frame(0xa2, b"\x01"), 9), [sim.Frame(0xa2, b"\x01\x00\x5e")])
        board.advance(20)
        self.assertEqual((board.state, board.remaining), (0, 94))

    def test_invalid_and_unsupported_requests(self):
        board = sim.Mainboard()
        for frame in (sim.Frame(0xa1, b"\x00\x00"), sim.Frame(0xa1, b"\x01"),
                      sim.Frame(0xb2, b"\x02"), sim.Frame(0xa4, b"\x01")):
            self.assertEqual(board.receive(frame, 0), [sim.Frame(frame.command, b"\x00")])
        for cmd in (0xb5, 0xc6):
            self.assertEqual(board.receive(sim.Frame(cmd, b"\x01"), 0), [sim.Frame(cmd, b"\x02")])
        self.assertEqual(board.receive(sim.Frame(0xff, b"\x01"), 0), [])
        with self.assertRaises(ValueError):
            sim.Mainboard(state=1, remaining=0)
        with self.assertRaises(ValueError):
            board.advance(-1)

    def test_opaque_info_and_params(self):
        raw = b"\x00\xac\xac\xff"
        board = sim.Mainboard(info=raw, params=b"")
        self.assertEqual(board.receive(sim.Frame(0xb1, b"\x01"), 0), [sim.Frame(0xb1, b"\x01"+raw)])
        self.assertEqual(board.receive(sim.Frame(0xb3, b"\x01"), 0), [sim.Frame(0xb3, b"\x01")])
        self.assertEqual(board.receive(sim.Frame(0xb4, raw), 0), [sim.Frame(0xb4, b"\x01")])
        self.assertEqual(board.params, raw)
        self.assertEqual(board.panel("params", b"", 0), [sim.Frame(0xc5, b"")])

    def test_full_b3_and_full_c5_have_different_body_limits(self):
        board = sim.Mainboard(params=sim.pattern(4088))
        reply, = board.receive(sim.Frame(0xb3, b"\x01"), 0)
        self.assertEqual(len(sim.encode(reply)), 4096)
        event, = board.panel("params", sim.pattern(4089), 0)
        self.assertEqual(len(sim.encode(event)), 4096)
        self.assertEqual(board.receive(sim.Frame(0xb3, b"\x01"), 0), [sim.Frame(0xb3, b"\x02")])
        with self.assertRaises(ValueError):
            sim.Mainboard(info=b"x"*4089)

    def test_panel_events_and_ack_do_not_loop(self):
        board = sim.Mainboard()
        self.assertEqual(board.panel("start", 60, 0), [sim.Frame(0xc2, b"\x00\x3c")])
        self.assertEqual(board.panel("pause", None, 2), [sim.Frame(0xc3, b"\x00\x3a")])
        self.assertEqual(board.panel("resume", None, 4), [sim.Frame(0xc2, b"\x00\x3a")])
        self.assertEqual(board.panel("stop", None, 5), [sim.Frame(0xc4, b"\x00\x39")])
        self.assertEqual(board.panel("expire", None, 6), [sim.Frame(0xc1, b"\x01")])
        self.assertEqual(board.receive(sim.Frame(0xc5, b"\x01"), 7), [])
        self.assertEqual(board.acks, 1)

    def test_rejected_panel_does_not_apply(self):
        board = sim.Mainboard()
        for action, value in (("start", 0), ("start", 65536), ("params", b"x"*4090), ("invalid", None)):
            with self.assertRaises(ValueError):
                board.panel(action, value, 0)
        self.assertEqual((board.state, board.remaining, board.params), (0, 0, b"\x03\x02\x21\x32\x04\x01\x01\x01"))


class SessionTests(unittest.TestCase):
    def query(self, session, now=0):
        return session.receive(bytes.fromhex("ACAC0004B201020F"), now)

    def test_literal_b2_round_trip(self):
        session = sim.Session(sim.Mainboard(state=1, remaining=100))
        self.query(session)
        self.assertEqual(session.emit_due(0), bytes.fromhex("ACAC0007B2010100640277"))
        self.assertEqual(session.emit_due(0), b"")
        self.assertEqual((session.rx_frames, session.tx_frames), (1, 1))

    def test_silent_then_normal_recovery(self):
        session = sim.Session()
        session.set_mode("silent")
        self.query(session)
        self.assertEqual(session.emit_due(10), b"")
        self.assertEqual(session.dropped, 1)
        session.set_mode("normal")
        self.query(session, 11)
        self.assertTrue(session.emit_due(11))

    def test_bad_checksum_and_truncated(self):
        for mode in ("bad-checksum", "truncated"):
            session = sim.Session()
            session.set_mode(mode)
            self.query(session)
            raw = session.emit_due(0)
            parser = sim.Stream()
            self.assertEqual(parser.feed(raw, 0), [])
            if mode == "bad-checksum":
                self.assertEqual(parser.bad_checksums, 1)
            else:
                parser.feed(b"", .25)
                self.assertEqual(parser.partial_timeouts, 1)

    def test_late_reply_and_mode_cancels_queued(self):
        session = sim.Session(late_ms=1500)
        session.set_mode("late")
        self.query(session)
        self.assertEqual(session.emit_due(1.499), b"")
        self.assertTrue(session.emit_due(1.5))
        self.query(session, 2)
        session.set_mode("silent")
        self.assertEqual(session.emit_due(10), b"")
        self.assertEqual(session.dropped, 1)

    def test_fragmentation_keeps_frame_order(self):
        session = sim.Session(chunk_size=2, gap_ms=10)
        session.set_mode("fragmented")
        session.enqueue(sim.Frame(0xb1, b"\x01\x00\xac"), 0)
        session.enqueue(sim.Frame(0xc5, b"\x00\x55"), 0)
        parser, frames = sim.Stream(), []
        for i in range(100):
            raw = session.emit_due(i*.01)
            if raw:
                self.assertLessEqual(len(raw), 2)
                frames += parser.feed(raw, i*.01)
        self.assertEqual(frames, [sim.Frame(0xb1, b"\x01\x00\xac"), sim.Frame(0xc5, b"\x00\x55")])
        self.assertEqual(session.tx_frames, 2)

    def test_bounded_pending_output(self):
        session = sim.Session()
        for i in range(1000):
            session.enqueue(sim.Frame(0xc5, b"\x01"), 0)
        self.assertEqual(session.summary()["pending"], 128)
        self.assertEqual(session.dropped, 872)

    def test_event_ack_has_no_output(self):
        session = sim.Session()
        session.receive(sim.encode(sim.Frame(0xc5, b"\x01")), 0)
        self.assertEqual(session.emit_due(0), b"")
        self.assertEqual(session.board.acks, 1)

    def test_new_c5_precedes_old_b3_reply_once(self):
        session = sim.Session(sim.Mainboard(params=b"old"))
        sim.handle_command(session, "race-params 00ACAC55", 0)
        session.receive(sim.encode(sim.Frame(0xb3, b"\x01")), 0)
        frames = sim.Stream().feed(session.emit_due(0) + session.emit_due(0), 0)
        self.assertEqual(frames, [sim.Frame(0xc5, b"\x00\xac\xac\x55"), sim.Frame(0xb3, b"\x01old")])
        self.assertIsNone(session.race_params)
        session.receive(sim.encode(sim.Frame(0xb3, b"\x01")), 1)
        self.assertEqual(sim.Stream().feed(session.emit_due(1), 1), [sim.Frame(0xb3, b"\x01\x00\xac\xac\x55")])

    def test_expiry_event_is_scheduled_once(self):
        session = sim.Session(sim.Mainboard(state=1, remaining=1))
        session.tick(1)
        self.assertEqual(session.emit_due(1), sim.encode(sim.Frame(0xc1, b"\x01")))
        session.tick(2)
        self.assertEqual(session.emit_due(2), b"")

    def test_invalid_timing_rejected(self):
        for args in (dict(chunk_size=0), dict(chunk_size=4097), dict(gap_ms=-1), dict(late_ms=60001)):
            with self.assertRaises(ValueError):
                sim.Session(**args)


class CommandAndTransportTests(unittest.TestCase):
    def test_read_only_status_and_panel_commands(self):
        session = sim.Session()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            sim.handle_command(session, "status", 0)
        self.assertIn('"mode": "normal"', output.getvalue())
        sim.handle_command(session, "panel start 120", 0)
        self.assertEqual(session.board.remaining, 120)
        sim.handle_command(session, "panel params-size 4089", 0)
        self.assertEqual(len(session.board.params), 4089)
        sim.handle_command(session, "panel params -", 0)
        self.assertEqual(session.board.params, b"")
        self.assertEqual(sim.handle_command(session, "burst 10 20", 0), (10, .02))
        self.assertEqual(sim.handle_command(session, "quit", 0), "quit")

    def test_invalid_commands_rejected(self):
        for command in ("mode unknown", "panel start 0", "panel params GG", "panel params-size 4090",
                        "panel pause 1", "burst 1001 20", "burst 1 19", "erase", "panel start"):
            with self.assertRaises(ValueError, msg=command):
                sim.handle_command(sim.Session(), command, 0)

    def test_partial_and_failed_writes(self):
        class Port:
            def __init__(self):
                self.output = bytearray()
            def write(self, raw):
                self.output.extend(raw[:2])
                return min(2, len(raw))
        port = Port()
        raw = sim.encode(sim.Frame(0xc5, b"\x00\xac"))
        sim.write_all(port, raw)
        self.assertEqual(port.output, raw)
        class BrokenPort:
            def write(self, raw):
                return 0
        with self.assertRaises(OSError):
            sim.write_all(BrokenPort(), raw)


if __name__ == "__main__":
    unittest.main()
