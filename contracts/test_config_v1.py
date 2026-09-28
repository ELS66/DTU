import copy
import json
import unittest
from pathlib import Path

from config_v1 import canonicalize_execution_config, verify_config_set


VECTOR = json.loads(Path(__file__).with_name("config-v1-vector.json").read_text(encoding="utf-8"))


class ConfigContractTest(unittest.TestCase):
    def test_golden_vector_and_point_order(self):
        config, canonical, digest = canonicalize_execution_config(VECTOR["executionConfig"])
        self.assertEqual(canonical, VECTOR["canonicalUtf8"])
        self.assertEqual(digest, VECTOR["sha256"])
        self.assertEqual([point["pointCode"] for point in config["points"]], [1, 2])
        reversed_config = copy.deepcopy(VECTOR["executionConfig"])
        reversed_config["points"].reverse()
        self.assertEqual(canonicalize_execution_config(reversed_config)[2], digest)

    def test_release_hash_and_mapping_changes(self):
        release = {
            "protocolVersion": 1,
            "releaseId": "1b37a40b-1736-475f-bf57-0861fcb07c5a",
            "revision": 12,
            "expiresAt": 1780000100000,
            "contentHash": VECTOR["sha256"],
            **VECTOR["executionConfig"],
        }
        self.assertEqual(verify_config_set(release)["contentHash"], VECTOR["sha256"])
        modified = copy.deepcopy(release)
        modified["points"][0]["slaveId"] = 2
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify_config_set(modified)

    def test_rejects_duplicate_points_and_unknown_fields(self):
        duplicate = copy.deepcopy(VECTOR["executionConfig"])
        duplicate["points"].append(copy.deepcopy(duplicate["points"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate point code"):
            canonicalize_execution_config(duplicate)
        extra_field = {**VECTOR["executionConfig"], "tenantId": "forged"}
        with self.assertRaisesRegex(ValueError, "fields"):
            canonicalize_execution_config(extra_field)


if __name__ == "__main__":
    unittest.main()
