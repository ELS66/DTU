"""Reference canonicalizer for the config/set v1 execution snapshot."""

from __future__ import annotations

import hashlib
import json
import re

RAW_TYPES = {"UINT16", "INT16", "UINT32", "INT32", "FLOAT32", "BOOL"}
BYTE_ORDERS = {"AB", "ABCD", "BADC", "CDAB", "DCBA"}
PORTS = {"RS485", "RS232", "TTL"}
PARITIES = {"NONE", "EVEN", "ODD"}
MAX_CONFIG_BYTES = 32768


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


def _serial(value: object) -> dict:
    data = _obj(value, "serial", {"port", "baudRate", "dataBits", "stopBits", "parity"})
    return {
        "port": _choice(data["port"], "port", PORTS),
        "baudRate": _int(data["baudRate"], "baud rate", 1200, 115200),
        "dataBits": _int(data["dataBits"], "data bits", 8, 8),
        "stopBits": _int(data["stopBits"], "stop bits", 1, 2),
        "parity": _choice(data["parity"], "parity", PARITIES),
    }


def _point(value: object) -> dict:
    data = _obj(value, "point", {"pointCode", "slaveId", "read", "write", "rawType", "byteOrder"})
    code = _int(data["pointCode"], "point code", 1, 65535)
    slave_id = _int(data["slaveId"], "slave ID", 1, 247)
    raw_type = _choice(data["rawType"], "raw type", RAW_TYPES)
    byte_order = _choice(data["byteOrder"], "byte order", BYTE_ORDERS)
    boolean = raw_type == "BOOL"
    wide = raw_type in {"UINT32", "INT32", "FLOAT32"}
    if (wide and byte_order == "AB") or (not wide and byte_order != "AB"):
        raise ValueError("invalid byte order and raw type")

    read = None
    if data["read"] is not None:
        mapping = _obj(data["read"], "read", {"function", "address", "count", "intervalMs"})
        fn = _int(mapping["function"], "read function", 1, 4)
        address = _int(mapping["address"], "read address", 0, 65535)
        count = _int(mapping["count"], "read count", 1, 2)
        if ((boolean and fn not in {1, 2}) or (not boolean and fn not in {3, 4})
                or count != (2 if wide else 1) or address + count > 65536):
            raise ValueError("invalid read mapping and raw type")
        read = {
            "function": fn,
            "address": address,
            "count": count,
            "intervalMs": _int(mapping["intervalMs"], "read interval", 100, 3600000),
        }

    write = None
    if data["write"] is not None:
        mapping = _obj(data["write"], "write", {"function", "address"})
        fn = _int(mapping["function"], "write function", 5, 16)
        address = _int(mapping["address"], "write address", 0, 65535)
        if fn != (5 if boolean else 16 if wide else 6) or address + (2 if wide else 1) > 65536:
            raise ValueError("invalid write mapping and raw type")
        write = {"function": fn, "address": address}
    if read is None and write is None:
        raise ValueError("point has no mapping")
    return {
        "pointCode": code,
        "slaveId": slave_id,
        "read": read,
        "write": write,
        "rawType": raw_type,
        "byteOrder": byte_order,
    }


def canonicalize_execution_config(value: object) -> tuple[dict, str, str]:
    data = _obj(value, "execution config", {"serial", "points"})
    if type(data["points"]) is not list or not 1 <= len(data["points"]) <= 128:
        raise ValueError("invalid point count")
    points = sorted((_point(point) for point in data["points"]), key=lambda point: point["pointCode"])
    if len({point["pointCode"] for point in points}) != len(points):
        raise ValueError("duplicate point code")
    config = {"serial": _serial(data["serial"]), "points": points}
    canonical = json.dumps({"schemaVersion": 1, **config}, separators=(",", ":"), ensure_ascii=True)
    if len(canonical.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError("config too large")
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return config, canonical, digest


def verify_config_set(value: object) -> dict:
    data = _obj(value, "config set", {
        "protocolVersion", "releaseId", "revision", "expiresAt", "contentHash", "serial", "points",
    })
    if data["protocolVersion"] != 1 or type(data["protocolVersion"]) is not int:
        raise ValueError("invalid protocol version")
    if type(data["releaseId"]) is not str or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            data["releaseId"]):
        raise ValueError("invalid release ID")
    revision = _int(data["revision"], "revision", 1, 0xFFFFFFFF)
    expires_at = _int(data["expiresAt"], "expiry", 1, 2**53 - 1)
    if type(data["contentHash"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", data["contentHash"]):
        raise ValueError("invalid content hash")
    config, _, digest = canonicalize_execution_config({
        "serial": data["serial"], "points": data["points"],
    })
    if digest != data["contentHash"]:
        raise ValueError("content hash mismatch")
    return {
        "protocolVersion": 1,
        "releaseId": data["releaseId"],
        "revision": revision,
        "expiresAt": expires_at,
        "contentHash": digest,
        **config,
    }
