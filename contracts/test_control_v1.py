import copy
import json
import unittest
from pathlib import Path

from control_v1 import (
    decode_control_json, parse_command_reply, parse_command_set, parse_config_reply,
    parse_telemetry_ack,
)


VECTOR = json.loads(Path(__file__).with_name("control-v1-vector.json").read_text(encoding="utf-8"))


class ControlContractTest(unittest.TestCase):
    def test_vectors(self):
        command = VECTOR["commandSet"]
        wire = json.dumps(command, separators=(",", ":")).encode("utf-8")
        self.assertEqual(parse_command_set(decode_control_json(wire)), command)
        self.assertEqual(parse_command_reply(VECTOR["commandReplyVerified"]), VECTOR["commandReplyVerified"])
        self.assertEqual(parse_command_reply(VECTOR["commandReplyFailed"]), VECTOR["commandReplyFailed"])
        self.assertEqual(parse_config_reply(VECTOR["configReplyApplied"]), VECTOR["configReplyApplied"])
        self.assertEqual(parse_telemetry_ack(VECTOR["telemetryAckStored"]), VECTOR["telemetryAckStored"])

    def test_raw_type_validation(self):
        command = copy.deepcopy(VECTOR["commandSet"])
        command["rawValue"] = True
        with self.assertRaisesRegex(ValueError, "integer raw value"):
            parse_command_set(command)
        command["rawType"] = "BOOL"
        self.assertTrue(parse_command_set(command)["rawValue"])
        command["rawType"] = "FLOAT32"
        command["rawValue"] = 1e40
        with self.assertRaisesRegex(ValueError, "float32 raw value"):
            parse_command_set(command)

    def test_status_and_ack_identity(self):
        reply = copy.deepcopy(VECTOR["commandReplyVerified"])
        reply["observedAt"] = None
        with self.assertRaisesRegex(ValueError, "observed value"):
            parse_command_reply(reply)
        applied = copy.deepcopy(VECTOR["configReplyApplied"])
        applied["appliedRevision"] = 11
        with self.assertRaisesRegex(ValueError, "applied revision"):
            parse_config_reply(applied)
        ack = copy.deepcopy(VECTOR["telemetryAckStored"])
        ack["sequence"] = 7
        with self.assertRaisesRegex(ValueError, "sequence"):
            parse_telemetry_ack(ack)
        ack["sequence"] = "9223372036854775808"
        with self.assertRaisesRegex(ValueError, "sequence"):
            parse_telemetry_ack(ack)

    def test_wire_rejects_duplicate_fields_and_invalid_encoding(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
            decode_control_json(b'{"status":"STORED","status":"REJECTED"}')
        with self.assertRaises(UnicodeDecodeError):
            decode_control_json(bytes((0xff, 0xfe)))
        with self.assertRaisesRegex(ValueError, "payload length"):
            decode_control_json(b'A' * 1025)


if __name__ == "__main__":
    unittest.main()
