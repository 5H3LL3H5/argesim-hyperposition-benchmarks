import tempfile
import unittest
from unittest.mock import patch

from scripts.c20_experiment import run_one


class C20CheckpointTests(unittest.TestCase):
    def test_resume_pins_inputs_source_and_python_runtime(self):
        spec = {
            "order_scenario": "OSc1",
            "plant_scenario": "PSc1",
            "seed": 1,
            "order_seed": 20,
            "order_count": 2,
            "trace": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            first = run_one(spec, "source-fingerprint", directory)
            with patch(
                "scripts.c20_experiment.C20Production", side_effect=AssertionError
            ):
                self.assertEqual(run_one(spec, "source-fingerprint", directory), first)
            for fingerprint, changed in (
                ("other-source", spec),
                ("source-fingerprint", {**spec, "order_count": 3}),
            ):
                with self.assertRaisesRegex(ValueError, "stale checkpoint"):
                    run_one(changed, fingerprint, directory)
            with (
                patch(
                    "scripts.c20_experiment.platform.python_version",
                    return_value="0.0.0",
                ),
                self.assertRaisesRegex(ValueError, "stale checkpoint"),
            ):
                run_one(spec, "source-fingerprint", directory)


if __name__ == "__main__":
    unittest.main()
