"""Rule boundaries, development-only calibration and persisted inference; no fit."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from ml.src import recommendation_engine as engine
from ml.src import model_inference as inference


class RecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thresholds = engine.load_thresholds()

    def result(self, value, current=40):
        return engine.recommend(value, current, thresholds=self.thresholds)

    def test_calibration_development_only(self):
        original = pd.read_csv
        reads = []
        def guarded(path, *args, **kwargs):
            reads.append(Path(path).name)
            if Path(path).name not in ("energy_train.csv", "energy_validation.csv"):
                raise AssertionError("Unexpected CSV access")
            return original(path, *args, **kwargs)
        with patch.object(pd, "read_csv", side_effect=guarded):
            calculated = engine.calibrate_thresholds()
        self.assertEqual(reads, ["energy_train.csv", "energy_validation.csv"])
        self.assertEqual(calculated, self.thresholds)
        values = np.concatenate([original(inference.ROOT / f"data/processed/energy_{s}.csv")["target_appliances_next"]
                                 for s in ("train", "validation")])
        self.assertEqual(len(values), calculated["calibration_rows"])
        for p in (50, 75, 90, 95):
            self.assertEqual(calculated[f"percentile_{p}"], float(np.percentile(values, p, method="linear")))

    def test_calibration_never_hashes_test(self):
        original = inference.sha256
        def guarded(path):
            self.assertNotEqual(Path(path).name, "energy_test.csv")
            return original(path)
        with patch.object(inference, "sha256", side_effect=guarded):
            engine.calibrate_thresholds()

    def test_exact_boundaries_and_all_levels(self):
        for p, below, at in [(75, "NORMAL", "ELEVATED"), (90, "ELEVATED", "HIGH"), (95, "HIGH", "VERY HIGH")]:
            value = self.thresholds[f"percentile_{p}"]
            with self.subTest(percentile=p):
                self.assertEqual(self.result(np.nextafter(value, -np.inf))["prediction"]["level"], below)
                self.assertEqual(self.result(value)["prediction"]["level"], at)
                self.assertEqual(self.result(np.nextafter(value, np.inf))["prediction"]["level"], at)

    def test_invalid_prediction_and_current(self):
        for bad in (np.nan, np.inf, -np.inf, -1, "40", None, True, 1+2j):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    self.result(bad)
                with self.assertRaises(ValueError):
                    self.result(40, bad)

    def test_missing_metadata(self):
        with self.assertRaises(FileNotFoundError):
            engine.load_thresholds(inference.ROOT / "ml/results/absent_phase14.json")

    def test_malformed_metadata(self):
        for key, value in [("percentile_75", np.nan), ("percentile_90", -1),
                           ("calibration_dataset", "test"), ("test_used", True),
                           ("forecast_horizon_minutes", 60), ("calibration_rows", 0),
                           ("calibration_input_sha256", {})]:
            bad = copy.deepcopy(self.thresholds)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                engine.recommend(40, 40, thresholds=bad)
        with self.assertRaises(ValueError):
            engine.recommend(40, 40, thresholds={})

    def test_trend(self):
        for predicted, current, direction, percent in [(60, 40, "rising", 50), (20, 40, "falling", -50),
                                                      (40, 40, "stable", 0), (40, 0, "rising", None), (0, 0, "stable", None)]:
            result = self.result(predicted, current)["trend"]
            self.assertEqual(result["direction"], direction)
            self.assertEqual(result["change_wh"], predicted-current)
            self.assertEqual(result["change_percent"], percent)

    def test_deterministic_scope_and_no_savings(self):
        for predicted in [0, *[self.thresholds[f"percentile_{p}"] for p in (75, 90, 95)]]:
            result = self.result(predicted)
            self.assertEqual(result, self.result(predicted))
            self.assertIs(result["scope"]["automatic_control"], False)
            self.assertIsNone(result["scope"]["estimated_savings"])
            self.assertEqual(result["recommendation"]["code"], result["prediction"]["level"].replace(" ", "_") + "_CONSUMPTION")
            text = json.dumps(result["recommendation"]).lower()
            for forbidden in ("kwh", "euro", "co2", "%", "will save", "setpoint", "occupancy"):
                self.assertNotIn(forbidden, text)
            json.dumps(result, allow_nan=False)

    def test_equal_percentiles_skip_empty_bands(self):
        thresholds = copy.deepcopy(self.thresholds)
        thresholds.update({f"percentile_{p}": 50 for p in (50, 75, 90, 95)})
        self.assertEqual(engine.recommend(50, 40, thresholds=thresholds)["prediction"]["level"], "VERY HIGH")


class InferenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = inference.load_final_model()
        cls.frame = pd.read_csv(inference.ROOT / "data/processed/energy_train.csv", nrows=3,
                                float_precision="round_trip")[cls.bundle[1]["ordered_feature_names"]]

    def test_single_row_real_model(self):
        actual = engine.predict_and_recommend(self.frame.iloc[:1], model_bundle=self.bundle)
        expected = inference.predict_next_appliances(self.frame.iloc[:1], self.bundle)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]["prediction"]["value_wh"], float(expected.iloc[0]))
        self.assertEqual(actual[0]["trend"]["current_wh"], float(self.frame.Appliances.iloc[0]))
        self.assertEqual(actual[0]["prediction"]["horizon_minutes"], 10)
        self.assertEqual(actual[0]["prediction"]["unit"], "Wh")
        self.assertEqual(actual, engine.predict_and_recommend(self.frame.iloc[:1], model_bundle=self.bundle))

    def test_batch_preserves_order_and_duplicate_index(self):
        frame = self.frame.iloc[[2, 0, 1]].copy()
        frame.index = [1, 1, 1]
        actual = engine.predict_and_recommend(frame, model_bundle=self.bundle)
        expected = inference.predict_next_appliances(frame, self.bundle)
        self.assertEqual([r["prediction"]["value_wh"] for r in actual], expected.tolist())
        self.assertEqual([r["trend"]["current_wh"] for r in actual], frame.Appliances.tolist())

    def test_malformed_features(self):
        invalid = [self.frame.drop(columns="lights"), self.frame.iloc[:, ::-1], self.frame.iloc[:0],
                   self.frame.assign(Appliances=-1), self.frame.assign(lights=np.nan), self.frame.to_numpy()]
        for frame in invalid:
            with self.subTest(kind=type(frame)), self.assertRaises((ValueError, TypeError)):
                engine.predict_and_recommend(frame, model_bundle=self.bundle)

    def test_artifact_and_phase11_unchanged(self):
        metadata = self.bundle[1]
        self.assertEqual(inference.sha256(inference.ARTIFACT_PATH), metadata["model_artifact_sha256"])
        path = inference.ROOT / "ml/results/phase11_final_test_evaluation.json"
        self.assertEqual(inference.sha256(path), metadata["input_sha256"][path.relative_to(inference.ROOT).as_posix()])


if __name__ == "__main__":
    unittest.main()
