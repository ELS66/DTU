"""Run one deterministic offline protocol round trip without an MQTT broker."""

import json
from pathlib import Path

from simulator import GatewaySimulator
from contracts.telemetry_v1 import decode


ROOT = Path(__file__).resolve().parents[1]
config_vector = json.loads((ROOT / "contracts/config-v1-vector.json").read_text(encoding="utf-8"))
control_vector = json.loads((ROOT / "contracts/control-v1-vector.json").read_text(encoding="utf-8"))
now_ms = 1780000000000
gateway = GatewaySimulator("demo-gateway", bytes(range(16)))

config_set = {
    "protocolVersion": 1,
    "releaseId": "1b37a40b-1736-475f-bf57-0861fcb07c5a",
    "revision": 12,
    "expiresAt": now_ms + 100000,
    "contentHash": config_vector["sha256"],
    **config_vector["executionConfig"],
}
print("config/reply", json.dumps(gateway.apply_config(config_set, now_ms)))

command_set = {**control_vector["commandSet"], "pointCode": 1}
print("command/reply", json.dumps(gateway.execute_command(command_set, now_ms + 1)))

frame = gateway.sample(now_ms + 2)
decoded = decode(frame)
print("telemetry topic", f"iot/v1/gateways/{gateway.gateway_id}/telemetry")
print("telemetry hex", frame.hex())
print("telemetry identity", decoded.boot_id.hex(), decoded.sequence)

ack = {**control_vector["telemetryAckStored"], "sequence": str(decoded.sequence)}
print("telemetry/ack accepted", gateway.receive_ack(ack))
