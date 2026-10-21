"""Protocol 1.8 mainboard simulator for an explicitly selected USB-to-3.3V-TTL port.

Run --help before wiring. This simulates a mainboard, not the ESP USB console.
No port is opened when this module is imported or when its tests run.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import heapq
import json
from pathlib import Path
import queue
import sys
import threading
import time

FRAME_MAX = 4096
PAYLOAD_MAX = FRAME_MAX - 7
MODES = ("normal", "silent", "bad-checksum", "fragmented", "truncated", "late")


@dataclass(frozen=True)
class Frame:
    command: int
    payload: bytes


def encode(frame: Frame) -> bytes:
    if not 0 <= frame.command <= 255 or len(frame.payload) > PAYLOAD_MAX:
        raise ValueError("command or payload outside protocol bounds")
    head = b"\xac\xac" + (len(frame.payload) + 3).to_bytes(2, "big")
    body = head + bytes([frame.command]) + frame.payload
    return body + (sum(body) & 0xffff).to_bytes(2, "big")


class Stream:
    """Independent bench codec: bounded partial frame, checksum resync and idle discard."""

    def __init__(self):
        self.buffer = bytearray()
        self.last_rx = 0.0
        self.bad_lengths = self.bad_checksums = self.partial_timeouts = 0

    def feed(self, data: bytes, now: float) -> list[Frame]:
        if self.buffer and now - self.last_rx >= .250:
            self.buffer.clear()
            self.partial_timeouts += 1
        frames = []
        for byte in data:
            self.buffer.append(byte)
            while self.buffer:
                if self.buffer[0] != 0xac:
                    del self.buffer[0]
                    continue
                if len(self.buffer) < 2:
                    break
                if self.buffer[1] != 0xac:
                    del self.buffer[0]
                    continue
                if len(self.buffer) < 4:
                    break
                length = int.from_bytes(self.buffer[2:4], "big")
                if length < 3 or length + 4 > FRAME_MAX:
                    self.bad_lengths += 1
                    del self.buffer[0]
                    continue
                total = length + 4
                if len(self.buffer) < total:
                    break
                raw = self.buffer[:total]
                if sum(raw[:-2]) & 0xffff != int.from_bytes(raw[-2:], "big"):
                    self.bad_checksums += 1
                    del self.buffer[0]
                    continue
                frames.append(Frame(raw[4], bytes(raw[5:-2])))
                del self.buffer[:total]
        if data:
            self.last_rx = now
        return frames


def pattern(size: int) -> bytes:
    if not 0 <= size <= PAYLOAD_MAX:
        raise ValueError("payload size must be 0..4089")
    return bytes(0xac if i % 5 == 0 else i % 256 for i in range(size))


class Mainboard:
    def __init__(self, info=b"\x01\x01", params=b"\x03\x02\x21\x32\x04\x01\x01\x01",
                 state=0, remaining=0, now=0.0):
        if state not in (0, 1, 3) or not 0 <= remaining <= 65535 or (state == 1 and not remaining):
            raise ValueError("invalid initial state/time")
        if len(info) > PAYLOAD_MAX - 1 or len(params) > PAYLOAD_MAX:
            raise ValueError("info/params too large")
        self.info, self.params = bytes(info), bytes(params)
        self.state, self.remaining, self.anchor = state, remaining, now
        self.acks = 0

    def advance(self, now: float) -> list[Frame]:
        if now < self.anchor:
            raise ValueError("monotonic clock moved backwards")
        if self.state != 1:
            self.anchor = now
            return []
        elapsed = int(now - self.anchor)
        self.anchor += elapsed
        self.remaining = max(0, self.remaining - elapsed)
        if not self.remaining:
            self.state = 0
            return [Frame(0xc1, b"\x01")]
        return []

    def receive(self, frame: Frame, now: float) -> list[Frame]:
        outgoing = self.advance(now)
        cmd, body = frame.command, frame.payload
        if cmd in (0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc7):
            if len(body) == 1 and body[0] <= 2:
                self.acks += 1
            return outgoing  # ACKs must never cause ACK loops.
        if cmd not in (*range(0xa1, 0xa5), *range(0xb1, 0xb6), 0xc6):
            return outgoing
        result = b"\x00"
        if cmd == 0xa1:
            if len(body) == 2 and int.from_bytes(body, "big"):
                self.remaining = int.from_bytes(body, "big")
                self.state, self.anchor, result = 1, now, b"\x01"
        elif cmd in (0xa2, 0xa3, 0xa4):
            if body == b"\x01" and (cmd != 0xa4 or self.remaining):
                self.state = {0xa2: 0, 0xa3: 3, 0xa4: 1}[cmd]
                self.anchor = now
                result = b"\x01" + self.remaining.to_bytes(2, "big")
        elif cmd in (0xb1, 0xb2, 0xb3):
            if body == b"\x01":
                if cmd == 0xb1:
                    result = b"\x01" + self.info
                elif cmd == 0xb2:
                    result = bytes([1, self.state]) + self.remaining.to_bytes(2, "big")
                else:
                    result = b"\x01" + self.params if len(self.params) < PAYLOAD_MAX else b"\x02"
        elif cmd == 0xb4:
            self.params, result = body, b"\x01"
        else:
            result = b"\x02"  # Trusted B5 clock and formal C6 identity are not invented.
        outgoing.append(Frame(cmd, result))
        return outgoing

    def panel(self, action: str, value, now: float) -> list[Frame]:
        if action == "start" and (not isinstance(value, int) or not 1 <= value <= 65535):
            raise ValueError("panel start seconds must be 1..65535")
        if action == "params" and (not isinstance(value, bytes) or len(value) > PAYLOAD_MAX):
            raise ValueError("panel params must be 0..4089 bytes")
        if action not in ("start", "pause", "resume", "stop", "expire", "params"):
            raise ValueError("unknown panel action")
        outgoing = self.advance(now)
        if action == "params":
            self.params = value
            outgoing.append(Frame(0xc5, value))
            return outgoing
        if action == "start":
            self.remaining, self.state = value, 1
        elif action == "pause":
            self.state = 3
        elif action == "resume":
            if not self.remaining:
                raise ValueError("no remaining time to resume")
            self.state = 1
        elif action == "stop":
            self.state = 0
        else:
            self.state = self.remaining = 0
        self.anchor = now
        cmd = {"start": 0xc2, "pause": 0xc3, "resume": 0xc2, "stop": 0xc4, "expire": 0xc1}[action]
        outgoing.append(Frame(cmd, b"\x01" if cmd == 0xc1 else self.remaining.to_bytes(2, "big")))
        return outgoing


class Session:
    """Single UART owner with bounded scheduled output and non-interleaved frame chunks."""

    def __init__(self, board=None, chunk_size=64, gap_ms=1, late_ms=1500):
        if not 1 <= chunk_size <= FRAME_MAX or not 0 <= gap_ms <= 10000 or not 0 <= late_ms <= 60000:
            raise ValueError("invalid output timing")
        self.board = board or Mainboard()
        self.stream = Stream()
        self.mode = "normal"
        self.chunk_size, self.gap = chunk_size, gap_ms / 1000
        self.late = late_ms / 1000
        self.pending = []
        self.active = None
        self.ordinal = self.rx_frames = self.tx_frames = self.dropped = 0
        self.race_params = None

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError("unknown mode")
        if mode != self.mode:
            self.dropped += len(self.pending) + int(self.active is not None)
            self.pending.clear()
            self.active = None
        self.mode = mode

    def enqueue(self, frame: Frame, now: float):
        if self.mode == "silent" or len(self.pending) + int(self.active is not None) >= 128:
            self.dropped += 1
            return
        raw = encode(frame)
        if self.mode == "bad-checksum":
            raw = raw[:-1] + bytes([raw[-1] ^ 1])
        elif self.mode == "truncated":
            raw = raw[:-2]
        chunks = deque(raw[i:i+self.chunk_size] for i in range(0, len(raw), self.chunk_size)) \
            if self.mode == "fragmented" else deque([raw])
        self.ordinal += 1
        heapq.heappush(self.pending, (now + (self.late if self.mode == "late" else 0),
                                     self.ordinal, chunks, self.gap if self.mode == "fragmented" else 0))

    def tick(self, now: float):
        for frame in self.board.advance(now):
            self.enqueue(frame, now)

    def receive(self, data: bytes, now: float) -> list[Frame]:
        frames = self.stream.feed(data, now)
        for frame in frames:
            self.rx_frames += 1
            for reply in self.board.receive(frame, now):
                if reply.command == 0xb3 and reply.payload[:1] == b"\x01" and self.race_params is not None:
                    # Snapshot the old B3 reply, then publish a newer C5 before that reply.
                    updated, self.race_params = self.race_params, None
                    for event in self.board.panel("params", updated, now):
                        self.enqueue(event, now)
                self.enqueue(reply, now)
        return frames

    def emit_due(self, now: float) -> bytes:
        if self.active is None:
            if not self.pending or self.pending[0][0] > now:
                return b""
            self.active = heapq.heappop(self.pending)
        due, ordinal, chunks, gap = self.active
        if due > now:
            return b""
        raw = chunks.popleft()
        if chunks:
            self.active = (now + gap, ordinal, chunks, gap)
        else:
            self.active = None
            self.tx_frames += 1
        return raw

    def summary(self):
        return dict(mode=self.mode, state=self.board.state, remaining=self.board.remaining,
                    params_bytes=len(self.board.params), rx_frames=self.rx_frames, tx_frames=self.tx_frames,
                    event_acks=self.board.acks, dropped=self.dropped,
                    pending=len(self.pending) + int(self.active is not None),
                    bad_lengths=self.stream.bad_lengths, bad_checksums=self.stream.bad_checksums,
                    partial_timeouts=self.stream.partial_timeouts)


def write_all(port, raw):
    offset = 0
    while offset < len(raw):
        written = port.write(raw[offset:])
        if not written or written > len(raw) - offset:
            raise OSError("serial write did not advance")
        offset += written


HELP = """status | mode normal|silent|bad-checksum|fragmented|truncated|late
panel start <1..65535> | panel pause|resume|stop|expire
panel params <hex or -> | panel params-size <0..4089>
race-params <hex or -> | race-params-size <0..4089> (arm next successful B3)
burst <1..1000 events> <20..5000 interval_ms> | quit
Changing mode discards queued simulator output. '-' means an empty opaque body."""


def handle_command(session, line, now):
    parts = line.split()
    if not parts:
        return None
    if parts == ["help"]:
        print(HELP, flush=True)
    elif parts == ["status"]:
        print(json.dumps(session.summary()), flush=True)
    elif parts == ["quit"]:
        return "quit"
    elif len(parts) == 2 and parts[0] == "mode":
        session.set_mode(parts[1])
    elif len(parts) == 2 and parts[0] in ("race-params", "race-params-size"):
        value = pattern(int(parts[1])) if parts[0] == "race-params-size" else \
            b"" if parts[1] == "-" else bytes.fromhex(parts[1])
        if len(value) > PAYLOAD_MAX:
            raise ValueError("race params must be 0..4089 bytes")
        session.race_params = value
    elif parts[0] == "panel" and len(parts) >= 2:
        action = parts[1]
        value = None
        if action in ("start", "params", "params-size"):
            if len(parts) != 3:
                raise ValueError("panel action requires one value")
            value = (b"" if parts[2] == "-" else bytes.fromhex(parts[2])) if action == "params" else int(parts[2])
            if action == "params-size":
                action, value = "params", pattern(value)
        elif len(parts) != 2:
            raise ValueError("unexpected panel arguments")
        for frame in session.board.panel(action, value, now):
            session.enqueue(frame, now)
    elif len(parts) == 3 and parts[0] == "burst":
        count, interval = int(parts[1]), int(parts[2])
        if not 1 <= count <= 1000 or not 20 <= interval <= 5000:
            raise ValueError("burst count/interval outside bounds")
        return count, interval / 1000
    else:
        raise ValueError("unknown command; use help")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="USB-to-TTL adapter COM port, not ESP USB console")
    parser.add_argument("--state", choices=("idle", "running", "paused"), default="idle")
    parser.add_argument("--remaining", type=int, default=0)
    parser.add_argument("--info-hex", default="0101", help="opaque B1 body, no result byte")
    params = parser.add_mutually_exclusive_group()
    params.add_argument("--params-hex", default=None)
    params.add_argument("--params-size", type=int, default=None, help="generated binary B3 body, 0..4088")
    parser.add_argument("--mode", choices=MODES, default="normal")
    parser.add_argument("--chunk-size", type=int, default=64)
    parser.add_argument("--gap-ms", type=float, default=1)
    parser.add_argument("--late-ms", type=float, default=1500)
    parser.add_argument("--duration", type=float, default=0, help="seconds; 0 runs until quit/Ctrl+C")
    parser.add_argument("--trace", type=Path, help="new JSONL metadata file; never overwrites or logs payload")
    args = parser.parse_args()
    try:
        if args.duration < 0:
            raise ValueError("duration must be nonnegative")
        body = bytes.fromhex(args.params_hex) if args.params_hex is not None else \
            pattern(args.params_size) if args.params_size is not None else b"\x03\x02\x21\x32\x04\x01\x01\x01"
        if len(body) > PAYLOAD_MAX - 1:
            raise ValueError("initial B3 body must be 0..4088; use panel params-size 4089 for the longest C5")
        started = time.monotonic()
        board = Mainboard(bytes.fromhex(args.info_hex), body, {"idle": 0, "running": 1, "paused": 3}[args.state],
                          args.remaining, started)
        session = Session(board, args.chunk_size, args.gap_ms, args.late_ms)
        session.set_mode(args.mode)
    except ValueError as error:
        parser.error(str(error))
    try:
        import serial
    except ImportError:
        parser.error("pyserial is required; use the configured ESP-IDF Python or install pyserial==3.5")
    commands = queue.Queue(maxsize=16)

    def read_commands():
        for line in sys.stdin:
            try:
                commands.put(line.strip(), timeout=.1)
            except queue.Full:
                print("Command queue full; command discarded", flush=True)

    trace = None
    port = None
    try:
        if args.trace:
            trace = args.trace.open("x", encoding="utf-8")
        port = serial.Serial(port=None, baudrate=9600, timeout=.002, write_timeout=5)
        port.dtr = port.rts = False
        port.port = args.port
        port.open()
        print(f"Mainboard simulator: {args.port} 9600 8N1; mode={args.mode}. Type help.", flush=True)
        threading.Thread(target=read_commands, daemon=True).start()
        burst_remaining, burst_interval, burst_at = 0, 0, 0
        while not args.duration or time.monotonic() - started < args.duration:
            now = time.monotonic()
            try:
                line = commands.get_nowait()
            except queue.Empty:
                line = None
            if line is not None:
                try:
                    result = handle_command(session, line, now)
                    if result == "quit":
                        break
                    if isinstance(result, tuple):
                        burst_remaining, burst_interval = result
                        burst_at = now
                except ValueError as error:
                    print(f"Command rejected: {error}", flush=True)
            session.tick(now)
            if burst_remaining and now >= burst_at:
                # Only the simulated board changes; no real device command is sent.
                if not session.board.remaining:
                    session.board.remaining = 60
                action = "pause" if session.board.state == 1 else "resume"
                for frame in session.board.panel(action, None, now):
                    session.enqueue(frame, now)
                burst_remaining -= 1
                burst_at = now + burst_interval
            data = port.read(256)
            observed = time.monotonic()
            frames = session.receive(data, observed)
            output = session.emit_due(observed)
            if output:
                write_all(port, output)
            if trace:
                for frame in frames:
                    trace.write(json.dumps(dict(at_ms=round((observed-started)*1000), direction="rx",
                                                command=f"{frame.command:02X}", payload_bytes=len(frame.payload))) + "\n")
                if output:
                    trace.write(json.dumps(dict(at_ms=round((observed-started)*1000),
                                                direction="tx_chunk", wire_bytes=len(output), mode=session.mode)) + "\n")
                trace.flush()
    except KeyboardInterrupt:
        pass
    except (OSError, serial.SerialException) as error:
        print(f"Simulator stopped: {error}", file=sys.stderr)
        return 1
    finally:
        if port is not None:
            port.close()
        if trace is not None:
            trace.close()
        print(json.dumps(session.summary()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
