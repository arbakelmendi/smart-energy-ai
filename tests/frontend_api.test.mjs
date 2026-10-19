// Transport fixtures verify client behavior only; they are not research evidence.
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { readFileSync } from "node:fs";
import { API_BASE_URL, ApiError, apiRequest, normalizeApiBaseUrl } from "../src/lib/api/client.ts";
import { getHealth, getModelInfo, getRecommendationThresholds, forecast, forecastWithRecommendation } from "../src/lib/api/smartEnergyApi.ts";

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
  const fixture = { model_name: "transport-fixture", feature_count: 42 };
  const calls = respond(fixture);
  assert.deepEqual(await getModelInfo(), fixture);
  assert.equal(calls[0].url, `${API_BASE_URL}/model/info`);
});

test("threshold data passes through, without client classification", async () => {
  const fixture = { calibration_dataset: "train+validation", percentiles_wh: {} };
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
