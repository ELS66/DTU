import unittest

from telemetry_v1 import Reading, Telemetry, decode, encode


SAMPLE = Telemetry(
    config_revision=12,
    boot_id=bytes(range(16)),
    sequence=7,
    sample_time_ms=1780000000000,
    replayed=False,
    time_trusted=True,
    points=(Reading(1, 2, 0, 0, 265), Reading(2, 6, 0, 50, True)),
)


class TelemetryContractTest(unittest.TestCase):
    def test_golden_vector(self):
        expected = (
            "44540101000000170000000c000102030405060708090a0b0c0d0e0f"
            "00000000000000070000019e70448800020002"
            "000102000000000000020109"
            "0002060000000032000101"
        )
        self.assertEqual(encode(SAMPLE).hex(), expected)
        self.assertEqual(decode(bytes.fromhex(expected)), SAMPLE)

    def test_rejects_invalid_payload_and_duplicate_points(self):
        frame = encode(SAMPLE)
        with self.assertRaises(ValueError):
            decode(frame[:-1])
        with self.assertRaises(ValueError):
            encode(Telemetry(12, bytes(16), 1, 1, False, True,
                             (Reading(1, 2, 0, 0, 1), Reading(1, 2, 0, 0, 2))))

    def test_bad_quality_has_no_false_value(self):
        sample = Telemetry(12, bytes(16), 1, 0, True, False,
                           (Reading(1, 2, 1, 0, None),))
        self.assertEqual(decode(encode(sample)), sample)


if __name__ == "__main__":
    unittest.main()
