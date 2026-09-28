"""Reference validators for the small JSON control messages in v1."""

from __future__ import annotations

import json
import math
import re

MAX_MESSAGE_BYTES = 1024
MAX_REVISION = 0xFFFFFFFF
MAX_SEQUENCE = 2**63 - 1
MAX_FLOAT32 = 3.4028234663852886e38
RAW_TYPES = {"UINT16", "INT16", "UINT32", "INT32", "FLOAT32", "BOOL"}
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def _obj(value: object, name: str, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"invalid {name} fields")
    return value


def _int(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"invalid {name}")
    return value


def _choice(value: object, name: str, choices: set[str]) -> str:
    if type(value) is not str or value not in choices:
        raise ValueError(f"invalid {name}")
    return value


def _uuid(value: object, name: str) -> str:
    if type(value) is not str or UUID.fullmatch(value) is None:
        raise ValueError(f"invalid {name}")
    return value


def _version(value: object) -> int:
    return _int(value, "protocol version", 1, 1)


def _error_code(value: object, required: bool) -> str | None:
    if value is None and not required:
        return None
    if type(value) is not str or ERROR_CODE.fullmatch(value) is None or not required:
        raise ValueError("invalid error code")
    return value


def _observed(value: object) -> bool | int | float:
    if type(value) is bool:
        return value
    if type(value) in (int, float) and abs(value) <= MAX_FLOAT32 and math.isfinite(value):
        return value
    raise ValueError("invalid observed raw value")


def validate_raw_value(raw_type: str, value: object) -> bool | int | float:
    if raw_type == "BOOL":
        if type(value) is not bool:
            raise ValueError("invalid boolean raw value")
        return value
    if raw_type == "FLOAT32":
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > MAX_FLOAT32:
            raise ValueError("invalid float32 raw value")
        return value
    limits = {
        "UINT16": (0, 65535),
        "INT16": (-32768, 32767),
        "UINT32": (0, 0xFFFFFFFF),
        "INT32": (-0x80000000, 0x7FFFFFFF),
    }
    low, high = limits[raw_type]
    return _int(value, "integer raw value", low, high)


def parse_command_set(value: object) -> dict:
    data = _obj(value, "command set", {
        "protocolVersion", "commandId", "configRevision", "expiresAt", "pointCode", "rawType", "rawValue",
    })
    raw_type = _choice(data["rawType"], "raw type", RAW_TYPES)
    return {
        "protocolVersion": _version(data["protocolVersion"]),
        "commandId": _uuid(data["commandId"], "command ID"),
        "configRevision": _int(data["configRevision"], "config revision", 1, MAX_REVISION),
        "expiresAt": _int(data["expiresAt"], "expiry", 1, 2**53 - 1),
        "pointCode": _int(data["pointCode"], "point code", 1, 65535),
        "rawType": raw_type,
        "rawValue": validate_raw_value(raw_type, data["rawValue"]),
    }


def parse_command_reply(value: object) -> dict:
    data = _obj(value, "command reply", {
        "protocolVersion", "commandId", "configRevision", "status", "errorCode",
        "observedRawValue", "observedAt",
    })
    status = _choice(data["status"], "command status", {
        "RECEIVED", "EXECUTING", "WRITE_ACKED", "VERIFIED", "FAILED", "REJECTED",
    })
    verified = status == "VERIFIED"
    if (verified and (data["observedRawValue"] is None or data["observedAt"] is None)) or (
            not verified and (data["observedRawValue"] is not None or data["observedAt"] is not None)):
        raise ValueError("invalid observed value and status")
    return {
        "protocolVersion": _version(data["protocolVersion"]),
        "commandId": _uuid(data["commandId"], "command ID"),
        "configRevision": _int(data["configRevision"], "config revision", 1, MAX_REVISION),
        "status": status,
        "errorCode": _error_code(data["errorCode"], status in {"FAILED", "REJECTED"}),
        "observedRawValue": _observed(data["observedRawValue"]) if verified else None,
        "observedAt": _int(data["observedAt"], "observed time", 1, 2**53 - 1) if verified else None,
    }


def parse_config_reply(value: object) -> dict:
    data = _obj(value, "config reply", {
        "protocolVersion", "releaseId", "revision", "status", "errorCode", "appliedRevision",
    })
    revision = _int(data["revision"], "revision", 1, MAX_REVISION)
    status = _choice(data["status"], "config status", {"RECEIVED", "APPLIED", "REJECTED"})
    applied = _int(data["appliedRevision"], "applied revision", 0, MAX_REVISION)
    if status == "APPLIED" and applied != revision:
        raise ValueError("applied revision mismatch")
    return {
        "protocolVersion": _version(data["protocolVersion"]),
        "releaseId": _uuid(data["releaseId"], "release ID"),
        "revision": revision,
        "status": status,
        "errorCode": _error_code(data["errorCode"], status == "REJECTED"),
        "appliedRevision": applied,
    }


def parse_telemetry_ack(value: object) -> dict:
    data = _obj(value, "telemetry ack", {
        "protocolVersion", "bootId", "sequence", "status", "errorCode",
    })
    boot_id = data["bootId"]
    sequence = data["sequence"]
    if type(boot_id) is not str or re.fullmatch(r"[0-9a-f]{32}", boot_id) is None:
        raise ValueError("invalid boot ID")
    if (type(sequence) is not str or re.fullmatch(r"[1-9][0-9]{0,18}", sequence) is None
            or int(sequence) > MAX_SEQUENCE):
        raise ValueError("invalid sequence")
    status = _choice(data["status"], "ack status", {"STORED", "REJECTED"})
    return {
        "protocolVersion": _version(data["protocolVersion"]),
        "bootId": boot_id,
        "sequence": sequence,
        "status": status,
        "errorCode": _error_code(data["errorCode"], status == "REJECTED"),
    }


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def decode_control_json(payload: bytes) -> object:
    if not 2 <= len(payload) <= MAX_MESSAGE_BYTES:
        raise ValueError("invalid payload length")
    return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_pairs,
                      parse_constant=_reject_constant)
