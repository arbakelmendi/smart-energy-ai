// Transport fixtures verify client behavior only; they are not research evidence.
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { readFileSync } from "node:fs";
import { API_BASE_URL, ApiError, apiRequest, normalizeApiBaseUrl } from "../src/lib/api/client.ts";
import { getHealth, getModelInfo, getRecommendationThresholds, forecast, forecastWithRecommendation, getModelComparison, getFeatureImportance } from "../src/lib/api/smartEnergyApi.ts";

const readResult = (name) => JSON.parse(readFileSync(new URL(`../ml/results/${name}`, import.meta.url), "utf8"));
const metadata = readResult("final_model_metadata.json");
const modelInfo = {
  model_name: metadata.model_name, model_family: metadata.model_family, target: metadata.target_column,
  unit: metadata.prediction_unit, forecast_horizon_minutes: metadata.forecast_horizon_minutes,
  feature_count: metadata.feature_count, ordered_feature_names: metadata.ordered_feature_names,
  final_held_out_metrics: metadata.held_out_test_metrics_from_phase11,
  model_selection_method: metadata.model_selection_basis, recommendation_capability: "Decision support", recommendation_available: true,
};
const savedThresholds = readResult("phase14_recommendation_thresholds.json");
const thresholdInfo = {
  calibration_dataset: savedThresholds.calibration_dataset, calibration_rows: savedThresholds.calibration_rows,
  target_column: savedThresholds.target_column, unit: savedThresholds.unit,
  forecast_horizon_minutes: savedThresholds.forecast_horizon_minutes,
  percentiles_wh: Object.fromEntries([50,75,90,95].map(p => [`percentile_${p}`, savedThresholds[`percentile_${p}`]])),
  level_definitions: savedThresholds.level_definitions, test_used: savedThresholds.test_used,
};

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const health = { status: "ok", model_available: true, recommendation_available: true, forecast_horizon_minutes: 10 };
function respond(payload, status = 200) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } });
  };
  return calls;
}

test("base URL defaults, whitespace, trailing slash and path prefixes", () => {
  assert.equal(normalizeApiBaseUrl(undefined), "http://127.0.0.1:8000");
  assert.equal(normalizeApiBaseUrl("  "), "http://127.0.0.1:8000");
  assert.equal(normalizeApiBaseUrl("https://example.invalid/api/// "), "https://example.invalid/api");
  for (const bad of ["invalid", "ftp://example.invalid", "https://user:pass@example.invalid", "https://example.invalid/?a=1", "https://example.invalid/#fragment"]) {
    assert.throws(() => normalizeApiBaseUrl(bad));
  }
});

test("health parses JSON and uses configured base without credentials", async () => {
  const calls = respond(health);
  assert.deepEqual(await getHealth(), health);
  assert.equal(calls[0].url, `${API_BASE_URL}/health`);
  assert.equal(calls[0].options.credentials, "omit");
  assert.ok(calls[0].options.signal instanceof AbortSignal);
});

test("model information passes through without fabricated defaults", async () => {
  const fixture = modelInfo;
  const calls = respond(fixture);
  assert.deepEqual(await getModelInfo(), fixture);
  assert.equal(calls[0].url, `${API_BASE_URL}/model/info`);
});

test("threshold data passes through, without client classification", async () => {
  const fixture = thresholdInfo;
  const calls = respond(fixture);
  assert.deepEqual(await getRecommendationThresholds(), fixture);
  assert.equal(calls[0].url, `${API_BASE_URL}/recommendations/thresholds`);
});

for (const [name, fn, path] of [["forecast", forecast, "/forecast"], ["recommendation", forecastWithRecommendation, "/forecast/recommendation"]]) {
  test(`${name} sends supplied features unchanged in the POST envelope`, async () => {
    // Serialization fixture only. Backend enforcement of complete input is tested separately.
    const features = { fixture_feature: 2 };
    const calls = respond({ transport_fixture: true });
    assert.deepEqual(await fn(features), { transport_fixture: true });
    assert.equal(calls[0].url, `${API_BASE_URL}${path}`);
    assert.equal(calls[0].options.method, "POST");
    assert.equal(calls[0].options.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(calls[0].options.body), { features });
  });
}

test("422 detail becomes a predictable ApiError", async () => {
  const fixture = { detail: [{ loc: ["body", "features"], msg: "finite value required", type: "finite_number" }] };
  respond(fixture, 422);
  await assert.rejects(getHealth(), error => error instanceof ApiError && error.status === 422 && error.message === "finite value required" && JSON.stringify(error.detail) === JSON.stringify(fixture));
});

test("503 and 500 do not expose server diagnostics in the message", async () => {
  for (const status of [503, 500]) {
    respond({ detail: "private-server-stack" }, status);
    await assert.rejects(getHealth(), error => error instanceof ApiError && error.status === status && !error.message.includes("private-server-stack"));
  }
});

test("network failure rejects explicitly, with no fake success", async () => {
  globalThis.fetch = async () => { throw new TypeError("network"); };
  await assert.rejects(getHealth(), error => error instanceof ApiError && error.status === null && error.message.includes("Backend unavailable"));
});

test("invalid success JSON fails explicitly", async () => {
  globalThis.fetch = async () => new Response("not-json");
  await assert.rejects(getHealth(), error => error instanceof ApiError && error.message.includes("invalid JSON"));
});

test("non-JSON HTTP errors preserve status", async () => {
  globalThis.fetch = async () => new Response("upstream unavailable", { status: 502 });
  await assert.rejects(getHealth(), error => error instanceof ApiError && error.status === 502);
});

test("nonfinite input is rejected before JSON could silently convert it to null", async () => {
  const calls = respond({});
  for (const value of [NaN, Infinity, -Infinity]) {
    await assert.rejects(forecast({ fixture_feature: value }), /finite numeric/);
  }
  assert.equal(calls.length, 0);
});

test("query cancellation signal is preserved", async () => {
  const calls = respond(health);
  const controller = new AbortController();
  await getHealth(controller.signal);
  assert.equal(calls[0].options.signal, controller.signal);
});

test("ambiguous endpoint URLs are rejected", async () => {
  await assert.rejects(apiRequest("//external.invalid/health"));
  await assert.rejects(apiRequest("health"));
});

test("API imports are SSR-safe without window", async () => {
  assert.equal(typeof globalThis.window, "undefined");
  assert.ok(API_BASE_URL.startsWith("http"));
});


test("analysis comparison parses committed validation metrics", async () => {
  const saved = readResult("phase10_tuning_summary.json");
  const lock = readResult("phase11_selection_lock.json");
  const payload = { evaluation_dataset: "validation", unit: "Wh", models: Object.entries(saved.validation_model_comparison).map(([model, metrics]) => ({model, ...metrics})),
    selected_model: lock.final_model_name, selection_metric: lock.selection_metric,
    selected_validation_rmse: lock.selected_validation_metrics.rmse, selection_basis: lock.selection_basis };
  const calls = respond(payload);
  assert.deepEqual(await getModelComparison(), payload);
  assert.equal(calls[0].url, `${API_BASE_URL}/analysis/model-comparison`);
});

test("feature importance parses saved values without causal reinterpretation", async () => {
  const saved = readResult("phase12_feature_importance.json");
  const fields = ["feature", "normalized_gain", "gain_rank", "permutation_mean", "permutation_std", "permutation_rank"];
  const payload = { model_name: saved.final_model_name, features: saved.features.map(f => Object.fromEntries(fields.map(k => [k, f[k]]))),
    gain_dataset: saved.gain_dataset, permutation_dataset: saved.explanation_dataset, normalized_gain_definition: saved.normalized_gain_definition,
    permutation_interpretation: saved.permutation_interpretation, permutation_std_definition: saved.permutation_std_definition, scope_note: "Predictive importance, not causal effect." };
  const calls = respond(payload);
  assert.deepEqual(await getFeatureImportance(), payload);
  assert.equal(calls[0].url, `${API_BASE_URL}/analysis/feature-importance`);
});

test("malformed research responses reject instead of supplying defaults", async () => {
  for (const fn of [getModelInfo, getRecommendationThresholds, getModelComparison, getFeatureImportance]) {
    respond({ malformed: true });
    await assert.rejects(fn(), error => error instanceof ApiError && /malformed research data/.test(error.message));
  }
});
