"""Strict feature-contract tests and native-model inference integration."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from ml.src import model_inference as inference


class FeatureContractTests(unittest.TestCase):
    def setUp(self):
        self.names = inference.read_json(inference.ROOT / "ml/results/feature_schema.json")["model_feature_columns"]
        # Validation fixture only; these values are never used as research evidence.
        self.frame = pd.DataFrame(np.zeros((1, 42)), columns=self.names)

    def test_valid_numeric_schema(self):
        self.assertIs(inference.validate_feature_frame(self.frame), self.frame)

    def test_missing_feature(self):
        with self.assertRaisesRegex(ValueError, "missing="):
            inference.validate_feature_frame(self.frame.drop(columns=self.names[0]))

    def test_unexpected_feature(self):
        with self.assertRaisesRegex(ValueError, "unexpected="):
            inference.validate_feature_frame(self.frame.assign(date=1))

    def test_reordered_features(self):
        with self.assertRaisesRegex(ValueError, "Feature order"):
            inference.validate_feature_frame(self.frame[self.names[::-1]])

    def test_duplicate_features(self):
        self.frame.columns = [self.names[0], *self.names[:-1]]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            inference.validate_feature_frame(self.frame)

    def test_nonnumeric_values(self):
        for value in ["bad", "10"]:
            with self.subTest(value=value):
                frame = self.frame.copy()
                frame[self.names[0]] = value
                with self.assertRaisesRegex(TypeError, "numeric"):
                    inference.validate_feature_frame(frame)

    def test_nan_and_infinity(self):
        for value in [np.nan, np.inf, -np.inf]:
            with self.subTest(value=value):
                frame = self.frame.copy()
                frame.iloc[0, 0] = value
                with self.assertRaisesRegex(ValueError, "finite"):
                    inference.validate_feature_frame(frame)

    def test_complex_and_boolean_values(self):
        for value in [1+2j, True]:
            frame = self.frame.copy()
            frame[self.names[0]] = value
            with self.assertRaisesRegex(TypeError, "real numeric"):
                inference.validate_feature_frame(frame)

    def test_array_and_empty_input_rejected(self):
        with self.assertRaises(TypeError):
            inference.validate_feature_frame(self.frame.to_numpy())
        with self.assertRaisesRegex(ValueError, "at least one"):
            inference.validate_feature_frame(self.frame.iloc[:0])


@unittest.skipUnless(inference.ARTIFACT_PATH.is_file(), "Generate the ignored artifact with save_final_model.py first")
class NativeInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = inference.load_final_model()
        cls.metadata = cls.bundle[1]
        cls.frame = pd.read_csv(inference.ROOT / "data/processed/energy_train.csv", nrows=128, float_precision="round_trip").loc[:, cls.metadata["ordered_feature_names"]]

    def test_metadata_and_order(self):
        schema = inference.read_json(inference.ROOT / "ml/results/feature_schema.json")
        self.assertEqual(self.metadata["feature_count"], 42)
        self.assertEqual(self.metadata["ordered_feature_names"], schema["model_feature_columns"])
        self.assertEqual(self.bundle[0].get_booster().feature_names, schema["model_feature_columns"])

    def test_real_feature_frame_predicts_wh(self):
        result = inference.predict_next_appliances(self.frame, self.bundle)
        self.assertEqual(len(result), 128)
        self.assertTrue(np.isfinite(result).all())
        self.assertEqual(result.attrs, {"unit": "Wh", "forecast_horizon_minutes": 10})
        np.testing.assert_array_equal(result.to_numpy(), self.bundle[0].predict(self.frame))

    def test_default_loader_predicts(self):
        expected = inference.predict_next_appliances(self.frame.iloc[:1], self.bundle)
        actual = inference.predict_next_appliances(self.frame.iloc[:1])
        np.testing.assert_array_equal(actual.to_numpy(), expected.to_numpy())

    def test_checksum_matches(self):
        self.assertEqual(inference.sha256(inference.ARTIFACT_PATH), self.metadata["model_artifact_sha256"])

    def test_corrupt_artifact_rejected(self):
        original = inference.sha256
        with patch.object(inference, "sha256", side_effect=lambda p: "wrong" if Path(p) == inference.ARTIFACT_PATH else original(p)):
            with self.assertRaisesRegex(ValueError, "artifact checksum"):
                inference.load_final_model()

    def test_wrong_metadata_contract_rejected(self):
        original = inference.read_json
        metadata = {**self.metadata, "ordered_feature_names": self.metadata["ordered_feature_names"][::-1]}
        with patch.object(inference, "read_json", side_effect=lambda p: metadata if Path(p) == inference.METADATA_PATH else original(p)):
            with self.assertRaisesRegex(ValueError, "contract"):
                inference.load_metadata()


from pathlib import Path
if __name__ == "__main__":
    unittest.main()
