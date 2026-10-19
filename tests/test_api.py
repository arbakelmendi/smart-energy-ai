"""FastAPI contract and direct-helper equivalence using TRAIN only; no fitting."""
import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import pandas as pd

from backend.main import app
from backend import services
from ml.src import model_inference as inference
from ml.src import recommendation_engine as recommendations


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = inference.load_final_model()
        cls.metadata = cls.bundle[1]
        cls.frame = pd.read_csv(inference.ROOT / "data/processed/energy_train.csv", nrows=1,
                                float_precision="round_trip")[cls.metadata["ordered_feature_names"]]
        cls.features = cls.frame.iloc[0].to_dict()
        cls.client = TestClient(app, raise_server_exceptions=False)

    def setUp(self):
        services.model_bundle.cache_clear()
        services.thresholds.cache_clear()
        self.payload = {"features": self.features.copy()}

    def tearDown(self):
        services.model_bundle.cache_clear()
        services.thresholds.cache_clear()

    def test_health_without_prediction(self):
        with patch.object(inference, "predict_next_appliances", side_effect=AssertionError("Health must not predict")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "model_available": True,
                                          "recommendation_available": True, "forecast_horizon_minutes": 10})

    def test_model_info_safe_and_metadata_derived(self):
        response = self.client.get("/model/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["model_name"], self.metadata["model_name"])
        self.assertEqual(data["model_family"], self.metadata["model_family"])
        self.assertEqual(data["feature_count"], 42)
        self.assertEqual(data["ordered_feature_names"], self.metadata["ordered_feature_names"])
        self.assertEqual(data["final_held_out_metrics"], self.metadata["held_out_test_metrics_from_phase11"])
        self.assertEqual(data["model_selection_method"], self.metadata["model_selection_basis"])
        self.assertNotIn(str(inference.ROOT), response.text)
        self.assertNotIn("sha256", response.text)

    def test_forecast_matches_direct_inference(self):
        response = self.client.post("/forecast", json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIsInstance(data["prediction_wh"], (int, float))
        self.assertEqual(data["prediction_wh"], float(inference.predict_next_appliances(self.frame, self.bundle).iloc[0]))
        self.assertEqual(data["unit"], "Wh")
        self.assertEqual(data["forecast_horizon_minutes"], 10)
        self.assertEqual(data["target"], "target_appliances_next")
        self.assertEqual(set(data), {"prediction_wh", "unit", "forecast_horizon_minutes", "target"})

    def test_recommendation_matches_direct_engine(self):
        response = self.client.post("/forecast/recommendation", json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        expected = recommendations.predict_and_recommend(self.frame, model_bundle=self.bundle)[0]
        self.assertEqual(response.json(), expected)
        self.assertEqual(set(response.json()), {"prediction", "thresholds_wh", "trend", "recommendation", "scope"})
        self.assertIs(response.json()["scope"]["automatic_control"], False)
        self.assertIsNone(response.json()["scope"]["estimated_savings"])

    def test_request_feature_order_is_irrelevant(self):
        reverse = {"features": dict(reversed(list(self.features.items())))}
        for route in ("/forecast", "/forecast/recommendation"):
            self.assertEqual(self.client.post(route, json=reverse).json(), self.client.post(route, json=self.payload).json())

    def test_missing_feature(self):
        del self.payload["features"]["lights"]
        self.assert_invalid(self.payload)

    def test_extra_feature(self):
        self.payload["features"]["occupancy"] = 1
        self.assert_invalid(self.payload)

    def test_nonnumeric_boolean_null_and_numeric_strings(self):
        for value in ("invalid", "40", True, None, [], {}):
            with self.subTest(value=value):
                self.payload["features"]["Appliances"] = value
                self.assert_invalid(self.payload)

    def test_numeric_json_integer_is_accepted(self):
        self.payload["features"]["Appliances"] = int(self.features["Appliances"])
        self.assertEqual(self.client.post("/forecast", json=self.payload).status_code, 200)

    def test_nonfinite_wire_payloads(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            self.payload["features"]["Appliances"] = value
            for route in ("/forecast", "/forecast/recommendation"):
                response = self.client.post(route, content=json.dumps(self.payload), headers={"Content-Type": "application/json"})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn("NaN", response.text)
                self.assertNotIn("Infinity", response.text)

    def test_negative_current_energy(self):
        self.payload["features"]["Appliances"] = -1
        self.assert_invalid(self.payload)

    def test_malformed_top_level_and_batch_rejected(self):
        for payload in ({}, {"features": {}}, {"features": self.features, "extra": 1},
                        {"features": [self.features]}, [self.payload], None):
            with self.subTest(payload_type=type(payload)):
                self.assert_invalid(payload)

    def test_malformed_json(self):
        response = self.client.post("/forecast", content='{bad', headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)

    def test_thresholds_match_phase14(self):
        response = self.client.get("/recommendations/thresholds")
        self.assertEqual(response.status_code, 200)
        data, expected = response.json(), recommendations.load_thresholds()
        self.assertEqual(data["calibration_dataset"], "train+validation")
        self.assertEqual(data["level_definitions"], expected["level_definitions"])
        self.assertEqual(data["percentiles_wh"], {k:expected[k] for k in ("percentile_50", "percentile_75", "percentile_90", "percentile_95")})
        self.assertIs(data["test_used"], False)

    def test_model_load_is_cached(self):
        with patch.object(inference, "load_final_model", wraps=inference.load_final_model) as loader:
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.post("/forecast", json=self.payload).status_code, 200)
            self.assertEqual(self.client.post("/forecast/recommendation", json=self.payload).status_code, 200)
            self.assertEqual(loader.call_count, 1)

    def test_model_absence_clean_503_and_recovery(self):
        with patch.object(inference, "load_final_model", side_effect=FileNotFoundError("private/path/model.json")):
            for route in ("/forecast", "/forecast/recommendation"):
                response = self.client.post(route, json=self.payload)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private/path", response.text)
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 503)
            self.assertIs(response.json()["model_available"], False)
            self.assertEqual(self.client.get("/model/info").status_code, 503)
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_model_checksum_failure_clean_503(self):
        original = inference.sha256
        with patch.object(inference, "sha256", side_effect=lambda p: "wrong" if p == inference.ARTIFACT_PATH else original(p)):
            response = self.client.post("/forecast", json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(str(inference.ROOT), response.text)

    def test_missing_thresholds_degrades_health_but_not_forecast(self):
        with patch.object(recommendations, "load_thresholds", side_effect=FileNotFoundError("private/thresholds")):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 503)
            self.assertTrue(response.json()["model_available"])
            self.assertFalse(response.json()["recommendation_available"])
            self.assertEqual(self.client.post("/forecast", json=self.payload).status_code, 200)
            self.assertEqual(self.client.post("/forecast/recommendation", json=self.payload).status_code, 503)
            self.assertEqual(self.client.get("/recommendations/thresholds").status_code, 503)

    def test_unexpected_inference_error_safe_500(self):
        with patch.object(inference, "predict_next_appliances", side_effect=RuntimeError("secret local path")):
            response = self.client.post("/forecast", json=self.payload)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Unable to complete the operation."})

    def test_negative_prediction_is_not_clipped(self):
        output = pd.Series([-1.0])
        with patch.object(inference, "predict_next_appliances", return_value=output):
            response = self.client.post("/forecast", json=self.payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["prediction_wh"], -1)
            response = self.client.post("/forecast/recommendation", json=self.payload)
            self.assertEqual(response.status_code, 500)
        # Synthetic model-output fixture verifies handling only; never research evidence.

    def test_docs_openapi_and_root(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["info"]["title"], "SmartEnergyAI API")
        self.assertEqual(data["info"]["version"], "1.0.0")
        for path in ("/health", "/model/info", "/forecast", "/forecast/recommendation", "/recommendations/thresholds"):
            self.assertIn(path, data["paths"])
        self.assertIn("RecommendationResponse", data["components"]["schemas"])
        self.assertEqual(self.client.get("/").json()["docs"], "/docs")

    def test_cors_local_allowed_external_rejected(self):
        headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "Content-Type"}
        response = self.client.options("/forecast", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], headers["Origin"])
        self.assertNotIn("access-control-allow-credentials", response.headers)
        headers["Origin"] = "https://untrusted.example"
        response = self.client.options("/forecast", headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_runtime_reads_no_dataset_and_never_fits(self):
        with patch.object(pd, "read_csv", side_effect=AssertionError("API must not read datasets")), patch.object(
                type(self.bundle[0]), "fit", side_effect=AssertionError("API must never fit")):
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.get("/model/info").status_code, 200)
            self.assertEqual(self.client.post("/forecast", json=self.payload).status_code, 200)
            self.assertEqual(self.client.post("/forecast/recommendation", json=self.payload).status_code, 200)

    def assert_invalid(self, payload):
        for route in ("/forecast", "/forecast/recommendation"):
            response = self.client.post(route, json=payload)
            self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
