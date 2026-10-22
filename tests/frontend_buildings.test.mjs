import assert from "node:assert/strict";
import { afterEach,test } from "node:test";
import { readFileSync } from "node:fs";
import { ApiError } from "../src/lib/api/client.ts";
import { createBuilding,deleteBuilding,getBuilding,getBuildings,parseBuildingId,updateBuilding } from "../src/lib/api/buildings.ts";

const building={id:7,name:"Persisted fixture",building_type:"Office",floor_area_m2:123.5,city:"City",description:null,created_at:"2026-01-01T12:00:00",updated_at:"2026-01-01T12:00:00"};
const original=globalThis.fetch;afterEach(()=>{globalThis.fetch=original;});
function respond(payload,status=200) { const calls=[];globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response(status===204?null:JSON.stringify(payload),{status,headers:{"Content-Type":"application/json"}});};return calls; }

test("list parses real metadata and sends credentials",async()=>{const calls=respond({buildings:[building]});assert.deepEqual(await getBuildings(),{buildings:[building]});assert.equal(calls[0].options.credentials,"include");assert.ok(calls[0].url.endsWith("/buildings"));});
test("empty list is preserved without examples",async()=>{respond({buildings:[]});assert.deepEqual(await getBuildings(),{buildings:[]});});
test("detail uses route id and included credentials",async()=>{const calls=respond(building);assert.deepEqual(await getBuilding(7),building);assert.ok(calls[0].url.endsWith("/buildings/7"));assert.equal(calls[0].options.credentials,"include");});
test("create sends supplied fields with CSRF protection",async()=>{const body={name:"New",floor_area_m2:2,building_type:"Other",city:null};const calls=respond(building,201);await createBuilding(body);assert.deepEqual(JSON.parse(calls[0].options.body),body);assert.equal(calls[0].options.method,"POST");assert.equal(calls[0].options.credentials,"include");assert.equal(calls[0].options.headers["X-SmartEnergy-CSRF"],"1");});
test("PATCH preserves explicit null and omission",async()=>{const calls=respond(building);await updateBuilding(7,{city:null});assert.deepEqual(JSON.parse(calls[0].options.body),{city:null});assert.equal(calls[0].options.method,"PATCH");});
test("DELETE accepts actual empty204 without fabricated JSON",async()=>{const calls=respond(null,204);assert.equal(await deleteBuilding(7),undefined);assert.equal(calls[0].options.method,"DELETE");assert.equal(calls[0].options.credentials,"include");assert.equal(calls[0].options.headers["X-SmartEnergy-CSRF"],"1");});
test("malformed metadata and fake operational data fail closed",async()=>{for(const value of [{},{buildings:[{...building,currentKwh:5}]},{buildings:[{...building,floor_area_m2:-1}]},{buildings:[{...building,created_at:"invalid"}]}]){respond(value);await assert.rejects(getBuildings(),e=>e instanceof ApiError&&/malformed building/.test(e.message));}});
test("nonfinite area rejected before JSON serialization",async()=>{for(const value of [NaN,Infinity,-Infinity]){await assert.rejects(createBuilding({name:"No",floor_area_m2:value}),TypeError);await assert.rejects(updateBuilding(7,{floor_area_m2:value}),TypeError);}});
test("404401403422 preserve ApiError and never supply fallback",async()=>{for(const status of [404,401,403,422]){respond({detail:"Safe error"},status);await assert.rejects(getBuilding(7),e=>e instanceof ApiError&&e.status===status);}});
test("network failure is explicit",async()=>{globalThis.fetch=async()=>{throw new TypeError("offline");};await assert.rejects(getBuildings(),ApiError);});
test("route ids cannot inject paths or unsafe integers",async()=>{for(const value of ["../auth/me","abc","0","-1","1e3","9007199254740993"]){assert.equal(parseBuildingId(value),null);}assert.equal(parseBuildingId("7"),7);await assert.rejects(getBuilding(NaN),TypeError);});
test("cancellation signal is forwarded",async()=>{const calls=respond({buildings:[]});const controller=new AbortController();await getBuildings(controller.signal);assert.equal(calls[0].options.signal,controller.signal);});
test("building pages remove old mock content and false metrics",()=>{const names=["../src/routes/buildings.index.tsx","../src/routes/buildings.$id.tsx","../src/components/building-management.tsx"];const text=names.map(n=>readFileSync(new URL(n,import.meta.url),"utf8")).join("\n");for(const value of ["mock-data","currentKwh","savingsPct","occupants","healthScore","buildTrend","confidence interval"]){assert.ok(!text.includes(value),value);}assert.ok(text.includes("No buildings yet"));assert.ok(text.includes("Measurement data has not been configured yet"));assert.ok(text.includes("Confirm delete"));});
