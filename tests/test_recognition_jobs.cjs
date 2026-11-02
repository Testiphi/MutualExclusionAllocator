'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createRecognitionJobs}=require('../miniapp/services/recognition_jobs');
const id='a'.repeat(32),key='request_key_0123456789';
function fixture(overrides={}) {
 let clock=1000,uploads=0,queries=0,cancels=0;const waits=[];
 const binding={server:'cn',version:'v1',identity:'visitor-generation-1',catalog:Array.from({length:5},(_,i)=>({big:'区'+i,small:'图'+i}))};
 const job=(state='succeeded')=>({id,server:'cn',catalog_version:'v1',state,expires_at:1000,result:{schema_version:1,server:'cn',catalog_version:'v1',status:'complete',slots:binding.catalog.map((m,i)=>({slot:i+1,state:'matched',...m}))}});
 const api={upload:async()=>{uploads++;return {id,server:'cn',catalog_version:'v1'};},query:async()=>{queries++;return job();},cancel:async()=>{cancels++;}};
 Object.assign(api,overrides);
 const client=createRecognitionJobs({api,currentBinding:()=>binding,createKey:async()=>key,now:()=>clock,wait:async ms=>{waits.push(ms);clock+=ms;}});
 return {client,api,binding,job,waits,get uploads(){return uploads;},get queries(){return queries;},get cancels(){return cancels;}};
}
const image={path:'tmp/one-screenshot',size:1024};
test('upload delegates once; five-slot normalization discards unrelated OCR fields',async()=>{
 const f=fixture();const value=await f.client.start(image);
 assert.equal(f.uploads,1);assert.equal(value.slots.length,5);assert.deepEqual(Object.keys(value),['server','version','slots']);assert.equal(f.client.state().phase,'finished');
});
test('queued/running polling uses original id; ambiguous slot remains at true position',async()=>{
 const f=fixture();let n=0;f.api.query=async()=>{const j=f.job(++n<3?'running':'succeeded');j.result.slots[1]={slot:2,state:'ambiguous',observed:['not for UI']};return j;};
 const value=await f.client.start(image);assert.equal(n,3);assert.equal(f.uploads,1);assert.equal(value.slots[1],null);assert.equal(value.slots[2].small,'图2');
});
test('query network failure resumes same job without upload; 429 respects normalized delay',async()=>{
 const f=fixture();let n=0;f.api.query=async()=>{if(++n===1)throw Error('offline');if(n===2)throw Object.assign(Error('rate limit'),{status:429,retryAfterMs:7000});return f.job();};
 await assert.rejects(f.client.start(image),/offline/);assert.equal(f.client.state().phase,'recoverable');
 await f.client.resume();assert.equal(f.uploads,1);assert.equal(n,3);assert.deepEqual(f.waits,[7000]);
});
test('lost upload response retains request_key and refuses blind reupload; recovery is injectable',async()=>{
 const f=fixture({upload:async()=>{throw Error('response lost');}});
 await assert.rejects(f.client.start(image),/response lost/);assert.equal(f.client.state().request_key,key);
 await assert.rejects(f.client.resume(),/服务端/);assert.equal(f.client.state().request_key,key);
 let recovered;f.api.recover=async input=>{recovered=input;return {id,server:'cn',catalog_version:'v1'};};await f.client.resume();assert.equal(recovered.request_key,key);
});
test('cancel during upload disposes late id without blocking a fresh attempt',async()=>{
 let resolve;const f=fixture({upload:()=>new Promise(r=>{resolve=r;})});const first=f.client.start(image);await new Promise(r=>setImmediate(r));f.client.cancel();
 f.api.upload=async()=>({id,server:'cn',catalog_version:'v1'});await f.client.start(image);
 resolve({id:'b'.repeat(32),server:'cn',catalog_version:'v1'});await assert.rejects(first,/停止/);await new Promise(r=>setImmediate(r));assert.equal(f.cancels,1);assert.equal(f.client.state().id,id);
});
test('suspend preserves job, foreground resumes query only and old response cannot publish',async()=>{
 let resolve;const f=fixture({query:()=>new Promise(r=>{resolve=r;})});const first=f.client.start(image);await new Promise(r=>setImmediate(r));f.client.suspend();
 f.api.query=async()=>f.job();await f.client.resume();resolve(f.job());await assert.rejects(first,/停止/);assert.equal(f.uploads,1);
});
test('changed identity/version, cross-server envelope, invalid order and unknown maps fail closed',async()=>{
 for(const mutate of [f=>{f.binding.identity='different';},f=>{f.binding.version='v2';},(f,j)=>{j.server='global';},(f,j)=>{j.result.slots[0].slot=5;},(f,j)=>{j.result.slots[0].small='unknown';}]) {
  const f=fixture();f.api.query=async()=>{const j=f.job();mutate(f,j);return j;};await assert.rejects(f.client.start(image));assert.equal(f.client.state().phase,'idle');
 }
});
test('expired/401/409 responses are not automatically retried or reauthenticated',async()=>{
 for(const status of [401,403,409,410]) {const f=fixture({query:async()=>{throw Object.assign(Error('rejected'),{status});}});await assert.rejects(f.client.start(image));assert.equal(f.client.state().phase,'idle');assert.equal(f.uploads,1);}
 const f=fixture();f.api.query=async()=>({...f.job(),expires_at:0});await assert.rejects(f.client.start(image),/到期/);
});
test('local snapshots and international OCR cannot start a native task',async()=>{
 for(const mutate of [b=>{b.server='global';},b=>{b.version='local-unfrozen-test';}]) {const f=fixture();mutate(f.binding);await assert.rejects(f.client.start(image),/原生会话/);assert.equal(f.uploads,0);}
});
test('bounded wait times out without losing original job; manual resume never creates another upload',async()=>{
 const f=fixture();f.api.query=async()=>f.job('running');await assert.rejects(f.client.start(image),e=>e.code==='timeout');
 assert.equal(f.client.state().phase,'recoverable');assert.equal(f.client.state().id,id);assert.equal(f.waits.reduce((a,b)=>a+b,0),180000);
 f.api.query=async()=>f.job();await f.client.resume();assert.equal(f.uploads,1);
});
