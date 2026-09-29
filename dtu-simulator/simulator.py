"""Small deterministic gateway model for protocol tests; no physical I/O."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.config_v1 import verify_config_set  # noqa: E402
from contracts.control_v1 import (  # noqa: E402
    parse_command_set, parse_telemetry_ack, validate_raw_value,
)
from contracts.telemetry_v1 import Reading, Telemetry, encode  # noqa: E402

RAW_TYPE_CODES = {"UINT16": 1, "INT16": 2, "UINT32": 3, "INT32": 4, "FLOAT32": 5, "BOOL": 6}
MAX_PENDING_FRAMES = 1000


class GatewaySimulator:
    def __init__(self, gateway_id: str, boot_id: bytes | None = None):
        if not gateway_id or "/" in gateway_id:
            raise ValueError("invalid gateway ID")
        self.gateway_id = gateway_id
        self.boot_id = boot_id if boot_id is not None else uuid4().bytes
        if len(self.boot_id) != 16:
            raise ValueError("boot ID must be 16 bytes")
        self.applied_revision = 0
        self.config: dict | None = None
        self.sequence = 0
        self.pending: dict[int, bytes] = {}
        self.raw_values: dict[int, bool | int | float | None] = {}
        self.releases: dict[str, tuple[dict, dict]] = {}
        self.commands: dict[str, tuple[dict, dict]] = {}

    def apply_config(self, message: object, now_ms: int) -> dict:
        release = verify_config_set(message)
        prior = self.releases.get(release["releaseId"])
        if prior is not None:
            if prior[0] == release:
                return prior[1].copy()
            return self._config_reply(release, "REJECTED", "RELEASE_ID_CONFLICT")
        if release["expiresAt"] <= now_ms:
            reply = self._config_reply(release, "REJECTED", "EXPIRED")
        elif release["revision"] <= self.applied_revision:
            reply = self._config_reply(release, "REJECTED", "REVISION_NOT_NEWER")
        else:
            self.config = release
            self.applied_revision = release["revision"]
            self.raw_values = {
                point["pointCode"]: (False if point["rawType"] == "BOOL" else 0)
                for point in release["points"] if point["read"] is not None
            }
            reply = self._config_reply(release, "APPLIED", None)
        self.releases[release["releaseId"]] = (release, reply)
        return reply.copy()

    def _config_reply(self, release: dict, status: str, error_code: str | None) -> dict:
        return {
            "protocolVersion": 1,
            "releaseId": release["releaseId"],
            "revision": release["revision"],
            "status": status,
            "errorCode": error_code,
            "appliedRevision": self.applied_revision,
        }

    def set_sensor_value(self, point_code: int, value: bool | int | float | None) -> None:
        if self.config is None:
            raise ValueError("no applied config")
        point = next((point for point in self.config["points"] if point["pointCode"] == point_code), None)
        if point is None or point["read"] is None:
            raise ValueError("point is not readable")
        self.raw_values[point_code] = None if value is None else validate_raw_value(point["rawType"], value)

    def execute_command(self, message: object, now_ms: int) -> dict:
        command = parse_command_set(message)
        prior = self.commands.get(command["commandId"])
        if prior is not None:
            if prior[0] == command:
                return prior[1].copy()
            return self._command_reply(command, "REJECTED", "COMMAND_ID_CONFLICT")
        if command["expiresAt"] <= now_ms:
            reply = self._command_reply(command, "REJECTED", "EXPIRED")
        elif command["configRevision"] != self.applied_revision or self.config is None:
            reply = self._command_reply(command, "REJECTED", "REVISION_MISMATCH")
        else:
            point = next((point for point in self.config["points"]
                          if point["pointCode"] == command["pointCode"]), None)
            if point is None or point["write"] is None:
                reply = self._command_reply(command, "REJECTED", "POINT_NOT_WRITABLE")
            elif point["rawType"] != command["rawType"]:
                reply = self._command_reply(command, "REJECTED", "TYPE_MISMATCH")
            elif point["read"] is None:
                reply = self._command_reply(command, "WRITE_ACKED", None)
            else:
                self.raw_values[command["pointCode"]] = command["rawValue"]
                reply = self._command_reply(command, "VERIFIED", None, command["rawValue"], now_ms)
        self.commands[command["commandId"]] = (command, reply)
        return reply.copy()

    @staticmethod
    def _command_reply(command: dict, status: str, error_code: str | None,
                       observed: bool | int | float | None = None,
                       observed_at: int | None = None) -> dict:
        return {
            "protocolVersion": 1,
            "commandId": command["commandId"],
            "configRevision": command["configRevision"],
            "status": status,
            "errorCode": error_code,
            "observedRawValue": observed,
            "observedAt": observed_at,
        }

    def sample(self, now_ms: int) -> bytes:
        if self.config is None or now_ms <= 0:
            raise ValueError("cannot sample without an applied config and trusted time")
        if len(self.pending) >= MAX_PENDING_FRAMES:
            raise ValueError("offline queue full")
        if self.sequence >= 2**63 - 1:
            raise ValueError("sequence exhausted; start a new boot session")
        readings = tuple(
            Reading(point["pointCode"], RAW_TYPE_CODES[point["rawType"]],
                    1 if self.raw_values[point["pointCode"]] is None else 0, 0,
                    self.raw_values[point["pointCode"]])
            for point in self.config["points"] if point["read"] is not None
        )
        if not readings:
            raise ValueError("config has no readable points")
        self.sequence += 1
        frame = encode(Telemetry(self.applied_revision, self.boot_id, self.sequence,
                                 now_ms, False, True, readings))
        self.pending[self.sequence] = frame
        return frame

    def resend_oldest(self) -> bytes | None:
        if not self.pending:
            return None
        frame = bytearray(next(iter(self.pending.values())))
        frame[44] |= 1  # replay flag; boot ID and sequence stay unchanged
        return bytes(frame)

    def receive_ack(self, message: object) -> bool:
        ack = parse_telemetry_ack(message)
        if ack["bootId"] != self.boot_id.hex():
            return False
        sequence = int(ack["sequence"])
        if sequence not in self.pending or ack["status"] != "STORED":
            return False
        del self.pending[sequence]
        return True
