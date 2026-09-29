"""MQTT topic adapter for the deterministic gateway simulator."""

from __future__ import annotations

import json
import time
from typing import Callable

from simulator import GatewaySimulator


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


class MqttGateway:
    def __init__(self, gateway: GatewaySimulator, client: object,
                 clock_ms: Callable[[], int] | None = None):
        self.gateway = gateway
        self.client = client
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.prefix = f"iot/v1/gateways/{gateway.gateway_id}/"

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            return
        for suffix in ("config/set", "command/set", "telemetry/ack"):
            client.subscribe(self.prefix + suffix, qos=1)
        self.resend_pending()

    def on_message(self, client, userdata, message):
        if not message.topic.startswith(self.prefix):
            return
        suffix = message.topic[len(self.prefix):]
        if suffix not in ("config/set", "command/set", "telemetry/ack"):
            return
        limit = 65536 if suffix == "config/set" else 1024
        if len(message.payload) > limit:
            raise ValueError("MQTT payload too large")
        payload = json.loads(message.payload.decode("utf-8"), object_pairs_hook=_unique_pairs)
        if suffix == "config/set":
            reply = self.gateway.apply_config(payload, self.clock_ms())
            self._publish_json("config/reply", reply)
        elif suffix == "command/set":
            reply = self.gateway.execute_command(payload, self.clock_ms())
            self._publish_json("command/reply", reply)
        else:
            if self.gateway.receive_ack(payload):
                self.resend_pending()

    def sample(self) -> None:
        self.client.publish(self.prefix + "telemetry", self.gateway.sample(self.clock_ms()),
                            qos=1, retain=False)

    def resend_pending(self) -> None:
        # Keep the original boot ID and sequence; only the replay flag changes.
        frame = self.gateway.resend_oldest()
        if frame is not None:
            self.client.publish(self.prefix + "telemetry", frame, qos=1, retain=False)

    def _publish_json(self, suffix: str, value: dict) -> None:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.client.publish(self.prefix + suffix, payload, qos=1, retain=False)
