"""Persistence gates and verification of the locally generated native artifact."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from ml.src import save_final_model as persistence
from ml.src import model_inference as inference


class PersistenceSafeguards(unittest.TestCase):
    def test_failed_reproduction_cannot_persist(self):
        with patch.object(persistence, "reconstruct_final_model", side_effect=ValueError("STOP: Phase 11 mismatch")), patch.object(persistence, "TemporaryDirectory") as directory:
            with self.assertRaisesRegex(ValueError, "STOP"):
                persistence.run_phase13()
            directory.assert_not_called()

    def test_existing_metadata_difference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "preserved"):
            persistence.verify_existing(persistence.RESULTS / "phase11_final_test_evaluation.json", b"different")


@unittest.skipUnless(inference.ARTIFACT_PATH.is_file(), "Generate the ignored artifact with save_final_model.py first")
class NativePersistenceTests(unittest.TestCase):
    def test_reload_matches_presave_verification_hash(self):
        model, metadata = inference.load_final_model()
        sample = pd.read_csv(inference.ROOT / "data/processed/energy_train.csv", nrows=128, float_precision="round_trip").loc[:, metadata["ordered_feature_names"]]
        self.assertEqual(persistence.prediction_sha256(model.predict(sample)), metadata["verification_sample"]["predictions_float32_le_sha256"])

    def test_metadata_record_and_source_integrity(self):
        record = inference.read_json(persistence.RESULT_PATH)
        metadata = inference.load_metadata()
        self.assertEqual(inference.sha256(inference.METADATA_PATH), record["metadata_sha256"])
        self.assertEqual(inference.sha256(inference.ARTIFACT_PATH), record["artifact_sha256"])
        self.assertTrue(record["phase11_metric_reproduction"]["passed"])
        self.assertEqual(record["reload_verification"]["max_absolute_prediction_difference_wh"], 0.0)
        self.assertEqual(record["reload_verification"]["verification_rows"], 128)
        self.assertEqual(metadata["development_rows"], metadata["train_rows"] + metadata["validation_rows"])
        self.assertFalse(metadata["test_used_for_fitting"])
        for path, expected in record["input_sha256"].items():
            with self.subTest(path=path):
                self.assertEqual(inference.sha256(inference.ROOT / path), expected)


if __name__ == "__main__":
    unittest.main()
