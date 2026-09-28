import copy
import json
import unittest
from pathlib import Path

from simulator import GatewaySimulator
from contracts.telemetry_v1 import decode


ROOT = Path(__file__).resolve().parents[1]
CONFIG_VECTOR = json.loads((ROOT / "contracts/config-v1-vector.json").read_text(encoding="utf-8"))
CONTROL_VECTOR = json.loads((ROOT / "contracts/control-v1-vector.json").read_text(encoding="utf-8"))
NOW = 1780000000000


def release() -> dict:
    return {
        "protocolVersion": 1,
        "releaseId": "1b37a40b-1736-475f-bf57-0861fcb07c5a",
        "revision": 12,
        "expiresAt": NOW + 100000,
        "contentHash": CONFIG_VECTOR["sha256"],
        **CONFIG_VECTOR["executionConfig"],
    }


class GatewaySimulatorTest(unittest.TestCase):
    def setUp(self):
        self.gateway = GatewaySimulator("gateway-test", bytes(range(16)))

    def test_config_command_telemetry_and_ack(self):
        config = release()
        self.assertEqual(self.gateway.apply_config(config, NOW)["status"], "APPLIED")
        self.assertEqual(self.gateway.apply_config(config, NOW)["status"], "APPLIED")

        command = copy.deepcopy(CONTROL_VECTOR["commandSet"])
        command["pointCode"] = 1
        self.assertEqual(self.gateway.execute_command(command, NOW + 1)["status"], "VERIFIED")
        first = decode(self.gateway.sample(NOW + 2))
        self.assertEqual(first.config_revision, 12)
        self.assertEqual(first.points[0].value, 300)
        self.assertEqual(first.points[1].value, False)
        self.assertEqual(len(self.gateway.pending), 1)

        self.gateway.set_sensor_value(1, 5)
        self.assertEqual(self.gateway.execute_command(command, NOW + 3)["observedRawValue"], 300)
        self.assertEqual(self.gateway.raw_values[1], 5)  # duplicate did not execute again
        conflicting = {**command, "rawValue": 6}
        self.assertEqual(self.gateway.execute_command(conflicting, NOW + 3)["errorCode"], "COMMAND_ID_CONFLICT")

        replay = decode(self.gateway.resend_oldest())
        self.assertEqual(replay.sequence, first.sequence)
        self.assertTrue(replay.replayed)
        ack = {**CONTROL_VECTOR["telemetryAckStored"], "sequence": str(first.sequence)}
        self.assertTrue(self.gateway.receive_ack(ack))
        self.assertIsNone(self.gateway.resend_oldest())

    def test_expired_and_stale_messages_do_not_change_state(self):
        expired = release()
        expired["expiresAt"] = NOW
        self.assertEqual(self.gateway.apply_config(expired, NOW)["errorCode"], "EXPIRED")
        self.assertEqual(self.gateway.applied_revision, 0)
        good = release()
        good["releaseId"] = "a0000000-0000-4000-8000-000000000000"
        self.assertEqual(self.gateway.apply_config(good, NOW)["status"], "APPLIED")
        stale = copy.deepcopy(CONTROL_VECTOR["commandSet"])
        stale["configRevision"] = 11
        self.assertEqual(self.gateway.execute_command(stale, NOW)["errorCode"], "REVISION_MISMATCH")
        self.gateway.set_sensor_value(1, None)
        telemetry = decode(self.gateway.sample(NOW + 1))
        self.assertEqual(telemetry.points[0].quality, 1)
        self.assertIsNone(telemetry.points[0].value)
        wrong_boot = {
            **CONTROL_VECTOR["telemetryAckStored"],
            "bootId": "ffffffffffffffffffffffffffffffff",
            "sequence": str(telemetry.sequence),
        }
        self.assertFalse(self.gateway.receive_ack(wrong_boot))
        self.assertEqual(len(self.gateway.pending), 1)


if __name__ == "__main__":
    unittest.main()
