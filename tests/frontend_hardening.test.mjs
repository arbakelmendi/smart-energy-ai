import assert from "node:assert/strict";
import {test,afterEach} from "node:test";
import {apiRequest,ApiError} from "../src/lib/api/client.ts";
const original=globalThis.fetch;afterEach(()=>{globalThis.fetch=original;});
test("a query cancellation signal must not disable the request deadline",async()=>{
 let captured;
 globalThis.fetch=(_url,{signal})=>{captured=signal;return new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(signal.reason),{once:true}));};
 const controller=new AbortController();let watchdog;const guard=new Promise((_resolve,reject)=>{watchdog=setTimeout(()=>reject(new Error('Request deadline was not enforced')),80);});
 try{await assert.rejects(Promise.race([apiRequest('/auth/me',{signal:controller.signal},20),guard]),e=>e instanceof ApiError&&/timed out/i.test(e.message));assert.equal(captured.aborted,true);assert.equal(controller.signal.aborted,false);}finally{clearTimeout(watchdog);controller.abort();}
});
test("explicit caller cancellation still propagates with the bounded deadline",async()=>{
 globalThis.fetch=(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(signal.reason),{once:true}));
 const controller=new AbortController();const reason=new DOMException('Cancelled','AbortError');const pending=apiRequest('/auth/me',{signal:controller.signal},100);controller.abort(reason);await assert.rejects(pending,e=>e===reason);
});

test("a stalled response body also retains its deadline",async()=>{
 let watchdog;
 globalThis.fetch=async(_url,{signal})=>({status:200,ok:true,json:()=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(signal.reason),{once:true}))});
 const guard=new Promise((_resolve,reject)=>{watchdog=setTimeout(()=>reject(new Error('Body deadline not enforced')),80);});
 try{await assert.rejects(Promise.race([apiRequest('/auth/me',{},20),guard]),e=>e instanceof ApiError&&/timed out/i.test(e.message));}finally{clearTimeout(watchdog);}
});
