'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const {utf8,decodeUtf8}=require('../miniapp/adapters/hash');
const {createNativeApi}=require('../miniapp/adapters/native_api');
const {verifyNativeSnapshot}=require('../miniapp/adapters/snapshot');
const {createNativeService}=require('../miniapp/services/native');
const {visibleCars}=require('../miniapp/lib/garage_view');
const core=require('../miniapp/shared/selection_core');
const config={enabled:true,kind:'fixture',origin:'http://127.0.0.1:8043',fixtureCode:'fixture-code-2',fixtureKey:'local-fixture-session-02'};
const examples=s=>JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../offline-evaluation/mini-api-20261102-01/snapshot-'+s+'.example.json'),'utf8'));
function harness(handler) {
 const calls=[],cache=new Map();let content=new Uint8Array([1,2,3]).buffer;
 const wx={getSystemInfoSync:()=>({platform:'devtools'}),getRandomValues:o=>o.success({randomValues:crypto.randomBytes(o.length).buffer.slice(0,o.length)}),getStorageSync:k=>cache.get(k),setStorageSync:(k,v)=>cache.set(k,structuredClone(v)),getFileSystemManager:()=>({readFile:o=>o.success({data:content})})};
 function call(o,upload){calls.push({url:o.url,header:o.header,data:o.data,name:o.name,formData:o.formData,upload});queueMicrotask(()=>{try{const r=handler(o,upload)||{};const data=r.rawText===undefined?JSON.stringify(r.body||{}):r.rawText;o.success({statusCode:r.status||200,header:r.header||{},data:upload?data:utf8(data).buffer});}catch(_){o.fail();}});return {abort(){}};}
 wx.request=o=>call(o,false);wx.uploadFile=o=>call(o,true);
 return {wx,calls,cache,setContent:x=>{content=x;}};
}
const session={schema_version:1,token:'memory-only-secret',token_type:'Bearer',identity:'test-session',expires_at:Math.floor(Date.now()/1000)+3600};
test('strict UTF-8 decoder roundtrips Chinese/emoji and rejects malformed bytes',()=>{
 assert.equal(decodeUtf8(utf8('中文🏎️\r\n')),'中文🏎️\r\n');for(const b of [[0xc0,0x80],[0xed,0xa0,0x80],[0xf4,0x90,0x80,0x80],[0xe4]])assert.throws(()=>decodeUtf8(new Uint8Array(b)));
});
test('fixed native session/query/multipart contract is used; no cookie, origin or identity goes on wire',async()=>{
 const h=harness((o,u)=>u?{body:{id:'a'.repeat(32)}}:{body:o.url.endsWith('/session')?session:{recovery:'found',id:'a'.repeat(32)}}),api=createNativeApi(h.wx,config);
 await api.session.ensure();assert.deepEqual(h.calls[0].data,{code:'fixture-code-2',request_key:'local-fixture-session-02',client_schema:1});
 const p={path:'tmp/a',size:3,request_key:'original_key_00001',server:'cn',catalog_version:'b'.repeat(64),identity:'test-session'};
 h.setContent(vm.runInNewContext('new Uint8Array([1,2,3]).buffer'));
 await api.jobs.upload(p);const c=h.calls[1];assert.equal(c.name,'image');assert.deepEqual(c.formData,{});assert.match(c.url,/\?server=cn&catalog_version=b+&request_key=original_key_00001$/);
 assert.deepEqual(Object.keys(c.header),['Authorization']);assert.equal(c.header.Authorization,'Bearer memory-only-secret');assert.ok(!c.url.includes('test-session'));
 h.setContent(new Uint8Array([4,5,6]).buffer);await assert.rejects(api.jobs.upload(p),/截图已变化/);assert.equal(h.calls.filter(c=>c.upload).length,1);
});
test('HTTP HTML errors preserve status and Retry-After seconds without leaking parser errors',async()=>{
 let html=false;const h=harness(o=>o.url.endsWith('/session')?{body:session}:html?{status:429,rawText:'<html>rate limit</html>',header:{'Retry-After':'5'}}:{status:429,body:{code:'RATE_LIMITED',detail:'限流'},header:{'Retry-After':'5'}}),api=createNativeApi(h.wx,config);await api.session.ensure();
 await assert.rejects(api.snapshot('cn'),e=>e.status===429&&e.code==='RATE_LIMITED'&&e.retryAfterMs===5000);
 html=true;await assert.rejects(api.snapshot('cn'),e=>e.status===429&&e.retryAfterMs===5000&&!e.message.includes('JSON'));
});
test('upload recovery waits reading then retries interrupted same bytes/key once',async()=>{
 let uploads=0,recoveries=0,clock=1000;const waits=[];
 const h=harness((o,u)=>{if(o.url.endsWith('/session'))return {body:session};if(u){if(++uploads===1)throw Error('response lost');return {body:{id:'a'.repeat(32)}};}return ++recoveries===1?{body:{recovery:'reading',retry_same_key:false},header:{'Retry-After':'2'}}:{body:{recovery:'interrupted',retry_same_key:true}};});
 const api=createNativeApi(h.wx,config,{now:()=>clock,wait:async ms=>{waits.push(ms);clock+=ms;}});await api.session.ensure();
 const p={path:'tmp/a',size:3,request_key:'original_key_00001',server:'cn',catalog_version:'b'.repeat(64),identity:'test-session'};
 await assert.rejects(api.jobs.upload(p));await api.jobs.recover(p);assert.equal(uploads,2);assert.deepEqual(waits,[2000]);
 assert.equal(new Set(h.calls.filter(c=>c.upload).map(c=>c.url)).size,1);
});
test('native snapshot verifies identity, original bytes, exact file list and international manifest',()=>{
 const cn=examples('cn'),global=examples('global');assert.equal(verifyNativeSnapshot(cn,'cn',cn.identity).data.tracks.length,83);assert.equal(verifyNativeSnapshot(global,'global',global.identity).data.tracks.length,44);
 for(const change of [v=>v.files['cars.json'].text+=' ',v=>v.identity='other',v=>v.files['extra']={text:'{}'}]){const v=structuredClone(cn);change(v);assert.throws(()=>verifyNativeSnapshot(v,'cn',cn.identity));}
});
test('verified snapshots are committed atomically, cached for offline compute, and never persist tokens',async()=>{
 let fail=false,bad=false;const h=harness(o=>{if(fail)throw Error('offline');if(o.url.endsWith('/session'))return {body:session};const server=o.url.includes('server=global')?'global':'cn',e=examples(server);e.identity=session.identity;if(bad&&server==='global')e.files['cars.global.json'].text+=' ';return {body:e};});
 const s=await createNativeService(h.wx,core,config);assert.equal(s.status().online,true);assert.equal(h.cache.size,2);assert.ok(!JSON.stringify([...h.cache.values()]).includes(session.token));
 const before=JSON.stringify([...h.cache]);bad=true;await assert.rejects(s.resume());assert.equal(JSON.stringify([...h.cache]),before);fail=true;
 const offline=await createNativeService(h.wx,core,config);assert.equal(offline.status().online,false);await assert.rejects(offline.recognize({path:'x',size:3}),/离线/);
});
test('garage sorting matches website numeric/unknown handling, class filter and title search',()=>{
 const cars=[{id:'乙',title:'Test Car',carClass:'S',score:100},{id:'甲',score:200,carClass:'A'},{id:'丙',score:null,carClass:'S'}];
 assert.deepEqual(visibleCars(cars,'','','score-desc').map(c=>c.id),['甲','乙','丙']);assert.deepEqual(visibleCars(cars,'','','score-asc').map(c=>c.id),['乙','甲','丙']);assert.equal(visibleCars(cars,'Test','S','alpha').length,1);
});
test('busy worker does not prevent resuming and confirming an existing result',async()=>{
 const cn=examples('cn'),data=JSON.parse(cn.files['gauntlet_data.json'].text),maps=data.tracks.map(t=>({big:t.大地图,small:t.小地图}));let worker='ready';
 const chosen=[];for(const m of maps)if(chosen.length<5&&!chosen.some(x=>x.big===m.big))chosen.push(m);
 const job={id:'a'.repeat(32),server:'cn',catalog_version:cn.catalog_version,state:'succeeded',expires_at:session.expires_at,result:{schema_version:1,server:'cn',catalog_version:cn.catalog_version,status:'complete',slots:chosen.map((m,i)=>({slot:i+1,state:'matched',...m}))}};
 const h=harness((o,u)=>{if(o.url.endsWith('/session'))return {body:session};if(o.url.includes('/snapshot?')){const e=examples(o.url.includes('server=global')?'global':'cn');e.identity=session.identity;return {body:e};}if(o.url.includes('/catalog?'))return {body:{server:'cn',identity:session.identity,version:cn.catalog_version,catalog_version:cn.catalog_version,maps,worker}};if(u)worker='busy';return {body:job};});
 const s=await createNativeService(h.wx,core,config);await s.recognize({path:'tmp/a',size:3});s.suspend();const result=await s.resume();assert.equal(result.slots.length,5);await s.verifyRecognition();assert.equal(s.diagnostics().network.uploads,1);
});
