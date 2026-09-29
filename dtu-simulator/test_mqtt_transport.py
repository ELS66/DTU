import json
import unittest
from types import SimpleNamespace

from mqtt_transport import MqttGateway
from simulator import GatewaySimulator
from test_simulator import NOW, release, CONTROL_VECTOR
from contracts.telemetry_v1 import decode


class FakeClient:
    def __init__(self):
        self.subscriptions = []
        self.publications = []

    def subscribe(self, topic, qos):
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos, retain):
        self.publications.append((topic, payload, qos, retain))


class MqttTransportTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.gateway = GatewaySimulator("gateway-test", bytes(range(16)))
        self.adapter = MqttGateway(self.gateway, self.client, lambda: NOW)
        self.prefix = "iot/v1/gateways/gateway-test/"

    def deliver(self, suffix, value):
        payload = json.dumps(value).encode("utf-8")
        self.adapter.on_message(self.client, None,
                                SimpleNamespace(topic=self.prefix + suffix, payload=payload))

    def test_topics_config_command_telemetry_and_ack(self):
        self.adapter.on_connect(self.client, None, None, 0)
        self.assertEqual({topic for topic, _ in self.client.subscriptions},
                         {self.prefix + suffix for suffix in
                          ("config/set", "command/set", "telemetry/ack")})
        self.deliver("config/set", release())
        self.assertEqual(json.loads(self.client.publications[-1][1])["status"], "APPLIED")
        command = {**CONTROL_VECTOR["commandSet"], "pointCode": 1}
        self.deliver("command/set", command)
        self.assertEqual(json.loads(self.client.publications[-1][1])["status"], "VERIFIED")
        self.adapter.sample()
        topic, frame, qos, retain = self.client.publications[-1]
        self.assertEqual((topic, qos, retain), (self.prefix + "telemetry", 1, False))
        self.assertEqual(decode(frame).sequence, 1)
        self.adapter.on_connect(self.client, None, None, 0)
        self.assertTrue(decode(self.client.publications[-1][1]).replayed)
        self.deliver("telemetry/ack", {
            "protocolVersion": 1, "bootId": self.gateway.boot_id.hex(),
            "sequence": "1", "status": "STORED", "errorCode": None,
        })
        self.assertEqual(self.gateway.pending, {})

    def test_foreign_topic_and_duplicate_json(self):
        self.adapter.on_message(self.client, None,
                                SimpleNamespace(topic="iot/v1/gateways/other/config/set",
                                                payload=b"{}"))
        self.assertEqual(self.client.publications, [])
        with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
            self.adapter.on_message(self.client, None,
                                    SimpleNamespace(topic=self.prefix + "command/set",
                                                    payload=b'{"protocolVersion":1,"protocolVersion":1}'))


if __name__ == "__main__":
    unittest.main()
